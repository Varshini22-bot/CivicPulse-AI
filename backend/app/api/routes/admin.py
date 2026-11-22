from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database.connection import get_db
from app.models import Report, Department, User, Category
from app.schemas import (
    ReportListItemOut, ReportDetailOut, DepartmentOut,
    StatusUpdateRequest, AIOverrideRequest, AssignmentRequest
)
from app.api.deps import get_current_active_admin
from app.services.report_service import ReportService
from app.api.routes.reports import serialize_report_item, serialize_report_detail

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
