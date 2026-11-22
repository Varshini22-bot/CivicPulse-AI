import os
import io
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, status
from PIL import Image
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models import Report, Category, User, Notification
from app.schemas import CategoryOut, ReportListItemOut, ReportDetailOut
from app.services.report_service import ReportService
from app.api.deps import get_current_user, get_optional_current_user
from app.core.config import settings
from app.core.limiter import limiter

router = APIRouter(prefix="/reports", tags=["Citizen Reports"])

def serialize_report_item(r: Report) -> dict:
    dept_name = None
    staff_name = None
    if r.assignments:
        active_assignment = r.assignments[-1]
        if active_assignment.department:
            dept_name = active_assignment.department.name
        if active_assignment.staff:
            staff_name = active_assignment.staff.name

    return {
        "id": r.id,
        "tracking_number": r.tracking_number,
        "title": r.title,
        "description": r.description,
        "category": r.category.name if r.category else "Unclassified",
        "category_code": r.category.code if r.category else "other",
        "verified_category": r.verified_category.name if r.verified_category else None,
        "latitude": r.latitude,
        "longitude": r.longitude,
        "address": r.address,
        "area": r.area,
        "status": r.status,
        "image_url": r.image_url,
        "resolution_image_url": r.resolution_image_url,
        "ai_severity": r.ai_severity,
        "human_severity": r.human_severity,
        "priority_score": r.priority_score,
        "priority_level": r.priority_level,
        "is_duplicate": r.is_duplicate,
        "is_synthetic": getattr(r, "is_synthetic", False),
        "created_at": r.created_at,
        "updated_at": r.updated_at,
        "resolved_at": r.resolved_at,
        "assigned_department": dept_name,
        "assigned_staff": staff_name
    }

def serialize_report_detail(r: Report) -> dict:
    base = serialize_report_item(r)
    
    # AI Prediction
    ai_pred = None
    if r.ai_prediction:
        p = r.ai_prediction
        pred_cat_name = p.predicted_category.name if p.predicted_category else "Unknown"
        pred_cat_code = p.predicted_category.code if p.predicted_category else "unknown"
        ai_pred = {
            "predicted_category_code": pred_cat_code,
            "predicted_category_name": pred_cat_name,
            "confidence": p.confidence,
            "raw_predictions": p.raw_predictions,
            "detected_features": p.detected_features,
            "model_name": p.model_name,
            "model_version": p.model_version,
            "inference_time_ms": p.inference_time_ms,
            "processing_status": p.processing_status
        }
        
    # Priority record
    prio_data = None
    if r.priority_record:
        pr = r.priority_record
        reasons = []
        if pr.explanation_json and "reasons" in pr.explanation_json:
            reasons = pr.explanation_json["reasons"]
        prio_data = {
            "severity_component": pr.severity_component,
            "safety_component": pr.safety_component,
            "location_risk_component": pr.location_risk_component,
            "community_impact_component": pr.community_impact_component,
            "age_component": pr.age_component,
            "final_score": pr.final_score,
            "priority_level": pr.priority_level,
            "reasons": reasons,
            "scoring_version": pr.scoring_version
        }

    # Duplicates
    duplicates = []
    for d in r.duplicate_links:
        target = d.target_report
        if target:
            duplicates.append({
                "id": d.id,
                "source_report_id": d.source_report_id,
                "target_report_id": d.target_report_id,
                "target_tracking_number": target.tracking_number,
                "target_title": target.title,
                "distance_meters": d.distance_meters,
                "category_match": d.category_match,
                "time_diff_hours": d.time_diff_hours,
                "composite_score": d.composite_score,
                "match_percentage": int(round(d.composite_score * 100)),
                "status": d.status,
                "notes": d.notes
            })

    # Audit history
    audits = []
    for a in r.audit_logs:
        user_name = "System AI Engine"
        if a.user_id:
            u = r.citizen if (r.citizen and r.citizen.id == a.user_id) else None
            user_name = u.full_name if u else "Municipal Officer"
        audits.append({
            "id": a.id,
            "action": a.action,
            "user_name": user_name,
            "previous_state": a.previous_state,
            "new_state": a.new_state,
            "notes": a.notes,
            "created_at": a.created_at
        })

    base["ai_prediction"] = ai_pred
    base["priority_breakdown"] = prio_data
    base["duplicate_candidates"] = duplicates
    base["audit_history"] = audits
    base["resolution_notes"] = r.resolution_notes
    return base

@router.get("/categories", response_model=List[CategoryOut])
def get_categories(db: Session = Depends(get_db)):
    """Fetch all supported civic issue categories."""
    return db.query(Category).order_by(Category.name.asc()).all()

@router.post("", response_model=ReportDetailOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def submit_report(
    request: Request,
    title: str = Form(..., min_length=5, max_length=255),
    description: str = Form(..., min_length=10),
    category_code: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    address: Optional[str] = Form(None),
    area: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Submit a citizen civic report. Accepts photographic evidence, coordinates,
    and runs the full AI inference pipeline (classification, severity, priority, duplicates).
    Enforces 10MB limit, magic-byte validation, and strips all privacy-sensitive EXIF metadata.
    """
    image_path = None
    if image:
        # Validate file format and size
        allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]
        ext = os.path.splitext(image.filename.lower())[1]
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image file format '{ext}'. Allowed formats: JPG, JPEG, PNG, WEBP."
            )

        # Enforce maximum 10MB limit and verify image magic bytes
        file_bytes = await image.read()
        max_size = 10 * 1024 * 1024  # 10 MB
        if len(file_bytes) > max_size:
            raise HTTPException(
                status_code=400,
                detail="Image file exceeds maximum permitted upload size of 10MB."
            )

        try:
            with Image.open(io.BytesIO(file_bytes)) as pil_img:
                pil_img.verify()
                fmt = (pil_img.format or "").upper()
                if fmt not in ["JPEG", "PNG", "WEBP"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid image format '{fmt}'. Only genuine JPEG, PNG, and WEBP files are accepted."
                    )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file failed image integrity validation (corrupted or polyglot payload)."
            )

        # Re-open verified image to strip EXIF/GPS metadata and save pure pixel raster
        with Image.open(io.BytesIO(file_bytes)) as source_img:
            mode = "RGBA" if source_img.mode in ("RGBA", "LA", "P") and ext in (".png", ".webp") else "RGB"
            clean_img = source_img.convert(mode)

            os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
            unique_filename = f"{uuid.uuid4()}{ext}"
            target_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

            save_format = "JPEG" if ext in [".jpg", ".jpeg"] else ("PNG" if ext == ".png" else "WEBP")
            clean_img.save(target_path, format=save_format)

        image_path = target_path

    # Delegate to ReportService
    citizen_id = current_user.id if current_user else None
    report = ReportService.create_report(
        db=db,
        citizen_id=citizen_id,
        title=title,
        description=description,
        category_code=category_code,
        latitude=latitude,
        longitude=longitude,
        address=address,
        area=area,
        image_path=image_path
    )

    return serialize_report_detail(report)

@router.get("/my", response_model=List[ReportListItemOut])
def get_my_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all reports submitted by the authenticated citizen."""
    reports = db.query(Report).filter(
        Report.citizen_id == current_user.id
    ).order_by(Report.created_at.desc()).all()
    
    return [serialize_report_item(r) for r in reports]

@router.get("/{report_id}", response_model=ReportDetailOut)
def get_report_by_id(
    report_id: str,
    db: Session = Depends(get_db)
):
    """Fetch complete report details with AI explainability and audit trail."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return serialize_report_detail(report)

@router.post("/{report_id}/withdraw", response_model=ReportDetailOut)
def withdraw_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Citizen withdraws an active report."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    if report.citizen_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to withdraw this report")

    if report.status in ["In Progress", "Resolved"]:
        raise HTTPException(status_code=400, detail="Cannot withdraw a report that is already In Progress or Resolved")

    updated = ReportService.update_status(
        db=db,
        report_id=report.id,
        new_status="Rejected",
        user_id=current_user.id,
        notes="Report withdrawn by citizen."
    )
    return serialize_report_detail(updated)
