from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database.connection import get_db
from app.models import Report, Department, User, Category, AuditLog
from app.schemas import (
    ReportListItemOut, ReportDetailOut, DepartmentOut,
    StatusUpdateRequest, AIOverrideRequest, AssignmentRequest
)
from app.api.deps import get_current_active_admin
from app.services.report_service import ReportService
from app.api.routes.reports import serialize_report_item, serialize_report_detail

class BulkActionRequest(BaseModel):
    report_ids: List[str]
    action: str = Field(..., pattern="^(change_status|assign_department|mark_duplicate)$")
    status: Optional[str] = None
    department_id: Optional[str] = None
    canonical_report_id: Optional[str] = None
    notes: Optional[str] = None

class ResolutionAuditDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(confirm|reject_reopen)$")
    notes: Optional[str] = None

router = APIRouter(prefix="/admin", tags=["Municipal Operations"])

@router.get("/reports")
def list_admin_reports(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin)
):
    """
    Searchable, filterable, paginated municipal issue ledger.
    """
    query = db.query(Report)

    if status:
        query = query.filter(Report.status == status)
    if priority:
        query = query.filter(Report.priority_level == priority)
    if category_id:
        query = query.filter(Report.category_id == category_id)
    if area:
        query = query.filter(Report.area == area)
    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Report.tracking_number.ilike(search_fmt),
                Report.title.ilike(search_fmt),
                Report.description.ilike(search_fmt),
                Report.address.ilike(search_fmt)
            )
        )

    total_count = query.count()

    # Sorting
    if hasattr(Report, sort_by):
        col = getattr(Report, sort_by)
        query = query.order_by(col.desc() if sort_dir == "desc" else col.asc())
    else:
        query = query.order_by(Report.created_at.desc())

    offset = (page - 1) * limit
    reports = query.offset(offset).limit(limit).all()

    return {
        "items": [serialize_report_item(r) for r in reports],
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit if total_count > 0 else 1
    }

@router.get("/reports/{report_id}", response_model=ReportDetailOut)
def get_admin_report_detail(
    report_id: str,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin)
):
    """Detailed municipal operational view with audit history and AI verification."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return serialize_report_detail(report)

@router.patch("/reports/{report_id}/status", response_model=ReportDetailOut)
def update_report_status(
    report_id: str,
    payload: StatusUpdateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin)
):
    """Transition issue status with mandatory audit logging and SLA update."""
    updated = ReportService.update_status(
        db=db,
        report_id=report_id,
        new_status=payload.status,
        user_id=admin_user.id,
        notes=payload.notes,
        resolution_image_url=payload.resolution_image_url
    )
    return serialize_report_detail(updated)

@router.post("/reports/{report_id}/override", response_model=ReportDetailOut)
def override_ai_prediction(
    report_id: str,
    payload: AIOverrideRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin)
):
    """Human-in-the-loop override of AI category classification or severity score."""
    updated = ReportService.override_ai_prediction(
        db=db,
        report_id=report_id,
        user_id=admin_user.id,
        verified_category_code=payload.verified_category_code,
        human_severity=payload.human_severity,
        notes=payload.notes
    )
    return serialize_report_detail(updated)

@router.post("/reports/{report_id}/assign", response_model=ReportDetailOut)
def assign_report(
    report_id: str,
    payload: AssignmentRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin)
):
    """Dispatch report to a municipal department and staff member."""
    updated = ReportService.assign_report(
        db=db,
        report_id=report_id,
        department_id=payload.department_id,
        staff_id=payload.staff_id,
        admin_user_id=admin_user.id,
        notes=payload.notes
    )
    return serialize_report_detail(updated)

@router.get("/departments", response_model=List[DepartmentOut])
def get_departments_and_staff(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin)
):
    """Retrieve all municipal departments and active field personnel."""
    return db.query(Department).all()

@router.post("/reset-demo-data")
def reset_demo_data(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin)
):
    """
    Safely resets transactional civic reports, re-seeding the realistic
    Bengaluru municipal demo dataset.
    """
    from app.database.seed_data import seed_database
    seed_database(db, force=True)
    return {
        "status": "success",
        "message": "Demo dataset reseeded successfully with 140+ Bengaluru civic reports."
    }

@router.post("/reports/bulk-action")
def execute_bulk_action(
    payload: BulkActionRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin)
):
    """
    Executes municipal bulk operations across multiple tickets:
    batch status change, department dispatch, or duplicate consolidation.
    """
    reports = db.query(Report).filter(Report.id.in_(payload.report_ids)).all()
    if not reports:
        raise HTTPException(status_code=404, detail="No matching reports found for bulk action.")

    updated_count = 0
    for r in reports:
        if payload.action == "change_status" and payload.status:
            ReportService.update_status(
                db=db,
                report_id=r.id,
                new_status=payload.status,
                user_id=admin_user.id,
                notes=payload.notes or f"Bulk status update to {payload.status}"
            )
            updated_count += 1
        elif payload.action == "assign_department" and payload.department_id:
            ReportService.assign_report(
                db=db,
                report_id=r.id,
                department_id=payload.department_id,
                admin_user_id=admin_user.id,
                notes=payload.notes or "Bulk department dispatch"
            )
            updated_count += 1
        elif payload.action == "mark_duplicate" and payload.canonical_report_id:
            r.is_duplicate = True
            r.canonical_report_id = payload.canonical_report_id
            db.add(AuditLog(
                report_id=r.id,
                user_id=admin_user.id,
                action="Marked as Duplicate (Bulk)",
                notes=payload.notes or f"Linked to canonical report {payload.canonical_report_id}"
            ))
            updated_count += 1

    db.commit()
    return {
        "status": "success",
        "action": payload.action,
        "affected_count": updated_count
    }

@router.get("/resolution-audit")
def list_resolution_audit_queue(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin)
):
    """
    Returns resolved or pending resolution audit queue with before/after photos and verification metrics.
    """
    reports = db.query(Report).filter(
        or_(
            Report.status == "Resolved",
            Report.resolution_verification_status.isnot(None),
            Report.resolution_image_url.isnot(None)
        )
    ).order_by(Report.updated_at.desc()).limit(50).all()

    items = []
    for r in reports:
        v_details = r.resolution_verification_details or {}
        items.append({
            "id": r.id,
            "tracking_number": r.tracking_number,
            "title": r.title,
            "category": r.category.name if r.category else "Unclassified",
            "category_code": r.category.code if r.category else "other",
            "area": r.area,
            "status": r.status,
            "image_url": r.image_url,
            "resolution_image_url": r.resolution_image_url,
            "resolution_verification_status": r.resolution_verification_status or "unverifiable",
            "verification_score": v_details.get("verification_score"),
            "scene_consistency": v_details.get("scene_consistency"),
            "defect_disappeared": v_details.get("defect_disappeared", True),
            "reasons": v_details.get("reasons", []),
            "resolved_at": r.resolved_at,
            "updated_at": r.updated_at
        })

    return items

@router.post("/reports/{report_id}/audit-resolution")
def audit_resolution_decision(
    report_id: str,
    payload: ResolutionAuditDecisionRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin)
):
    """
    Supervisor decision on a resolved issue:
    'confirm': Approves closure and confirms verified status.
    'reject_reopen': Rejects completion evidence and reopens ticket to 'In Progress'.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if payload.decision == "confirm":
        report.resolution_verification_status = "verified"
        db.add(AuditLog(
            report_id=report.id,
            user_id=admin_user.id,
            action="Resolution Audit: Confirmed",
            notes=payload.notes or "Municipal supervisor confirmed completion evidence."
        ))
    elif payload.decision == "reject_reopen":
        report.status = "In Progress"
        report.resolution_verification_status = "audit_rejected"
        db.add(AuditLog(
            report_id=report.id,
            user_id=admin_user.id,
            action="Resolution Audit: Rejected & Reopened",
            previous_state={"status": "Resolved"},
            new_state={"status": "In Progress"},
            notes=payload.notes or "Supervisor rejected resolution evidence; reopened for remedial work."
        ))

    db.commit()
    db.refresh(report)
    return serialize_report_detail(report)

