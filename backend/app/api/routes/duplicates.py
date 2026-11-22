from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models import DuplicateCandidate, Report, User, AuditLog
from app.schemas import DuplicateActionRequest
from app.api.deps import get_current_active_admin

router = APIRouter(prefix="/admin/duplicates", tags=["Duplicate Detection"])

@router.get("")
def list_duplicate_candidates(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin)
):
    """Retrieve all detected duplicate candidate pairings awaiting administrative review."""
    candidates = db.query(DuplicateCandidate).order_by(
        DuplicateCandidate.composite_score.desc()
    ).all()

    results = []
    for c in candidates:
        source = c.source_report
        target = c.target_report
        if source and target:
            results.append({
                "id": c.id,
                "source_report_id": c.source_report_id,
                "source_tracking_number": source.tracking_number,
                "source_title": source.title,
                "source_area": source.area,
                "source_status": source.status,
                "target_report_id": c.target_report_id,
                "target_tracking_number": target.tracking_number,
                "target_title": target.title,
                "target_area": target.area,
                "target_status": target.status,
                "distance_meters": c.distance_meters,
                "category_match": c.category_match,
                "time_diff_hours": c.time_diff_hours,
                "composite_score": c.composite_score,
                "match_percentage": int(round(c.composite_score * 100)),
                "status": c.status,
                "notes": c.notes,
                "created_at": c.created_at
            })
    return results

@router.post("/{candidate_id}/resolve")
def resolve_duplicate_candidate(
    candidate_id: str,
    payload: DuplicateActionRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_active_admin)
):
    """Confirm or reject a duplicate report suggestion."""
    link = db.query(DuplicateCandidate).filter(DuplicateCandidate.id == candidate_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Duplicate candidate link not found")

    link.status = payload.status
    link.resolved_by_user_id = admin_user.id
    if payload.notes:
        link.notes = f"{link.notes or ''} [Admin Decision: {payload.status}] {payload.notes}".strip()

    # If confirmed, link source as duplicate of canonical target
    if payload.status == "confirmed":
        source = link.source_report
        target = link.target_report
        if source and target:
            source.is_duplicate = True
            source.canonical_report_id = target.id
            
            # Audit log
            audit = AuditLog(
                report_id=source.id,
                user_id=admin_user.id,
                action="duplicate_confirmed",
                previous_state={"is_duplicate": False},
                new_state={"is_duplicate": True, "canonical_report_id": target.id},
                notes=f"Linked to canonical report #{target.tracking_number}."
            )
            db.add(audit)

    db.commit()
    return {"status": "success", "duplicate_candidate_id": candidate_id, "resolved_status": payload.status}
