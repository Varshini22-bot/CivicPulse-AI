import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models import (
    Report, Category, Department, Staff, AIPrediction, PriorityScore,
    DuplicateCandidate, Assignment, AuditLog, Notification, User
)
from app.ml.vision_classifier import classifier
from app.ml.pipeline import pipeline
from app.services.severity_service import SeverityService
from app.services.priority_service import PriorityService
from app.services.duplicate_service import DuplicateService
from app.core.config import settings

class ReportService:
    """
    Core orchestrator for civic issue ingestion, municipal workflow transitions,
    AI explainability, and audit compliance.
    """

    VALID_TRANSITIONS = {
        "Submitted": ["Under Review", "Rejected"],
        "Under Review": ["Verified", "Rejected"],
        "Verified": ["Assigned", "In Progress", "Rejected"],
        "Assigned": ["In Progress", "Under Review", "Rejected"],
        "In Progress": ["Resolved", "Assigned", "Under Review"],
        "Resolved": ["In Progress"],
        "Rejected": ["Under Review"]
    }

    @classmethod
    def generate_tracking_number(cls, db: Session) -> str:
        """Generate unique human-readable tracking number like CP-2026-0142."""
        count = db.query(Report).count()
        year = datetime.now().year
        return f"CP-{year}-{count + 1:04d}"

    @classmethod
    def create_report(
        cls,
        db: Session,
        citizen_id: Optional[str],
        title: str,
        description: str,
        category_code: str,
        latitude: float,
        longitude: float,
        address: Optional[str],
        area: Optional[str],
        image_path: Optional[str]
    ) -> Report:
        """
        Create a new report, trigger the AI computer vision pipeline,
        severity estimation, priority calculation, and duplicate scan.
        """
        # 1. Resolve category
        category = db.query(Category).filter(Category.code == category_code).first()
        if not category:
            category = db.query(Category).filter(Category.code == "other").first()
            if not category:
                category = db.query(Category).first()

        tracking_num = cls.generate_tracking_number(db)
        
        # 2. Run Computer Vision inference through multi-model CivicVisionPipeline
        vision_result = pipeline.process_report(
            image_path=image_path,
            description=description,
            citizen_category_code=category.code if category else "other",
            db=db
        )

        pred_cat_code = category.code if category else "other"
        sugg_cat_code = vision_result.get("ai_suggested_category", pred_cat_code)
        suggested_category = db.query(Category).filter(Category.code == sugg_cat_code).first()
        if not suggested_category:
            suggested_category = category

        confidence = vision_result["confidence"]
        visual_features = vision_result.get("detected_features", {})

        # 3. Estimate Severity (1-10) with optional localized defect metrics
        sev_result = SeverityService.estimate_severity(
            category_code=pred_cat_code,
            confidence=confidence,
            visual_features=visual_features,
            description=description,
            db=db,
            detection_count=vision_result.get("detection_count"),
            relative_box_area=vision_result.get("relative_box_area")
        )
        ai_severity = sev_result["severity_score"]

        # 4. Calculate Priority Score (0-100)
        prio_result = PriorityService.calculate_priority(
            severity_score=ai_severity,
            category_safety_weight=category.safety_weight if category else 0.5,
            location_text=f"{address or ''} {area or ''}",
            supporting_reports_count=1,
            created_at=datetime.now(timezone.utc),
            description=description
        )

        # 5. Create Report entity
        report = Report(
            id=str(uuid.uuid4()),
            tracking_number=tracking_num,
            citizen_id=citizen_id,
            title=title.strip(),
            description=description.strip(),
            category_id=category.id,
            latitude=latitude,
            longitude=longitude,
            address=address,
            area=area or "Bengaluru Central",
            status="Submitted",
            image_url=image_path,
            ai_severity=ai_severity,
            priority_score=prio_result["final_score"],
            priority_level=prio_result["priority_level"],
            is_synthetic=False,
            location=f"POINT({longitude} {latitude})",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(report)
        db.flush()

        # 6. Save AI Prediction with model attribution and detection boxes
        prediction_record = AIPrediction(
            report_id=report.id,
            predicted_category_id=category.id,
            suggested_category_id=suggested_category.id if suggested_category else None,
            confidence=confidence,
            detected_features=visual_features,
            raw_predictions=vision_result.get("raw_predictions", {}),
            detections=vision_result.get("detections", []),
            model_name=vision_result.get("analyzer_name", "CivicVisionPipeline"),
            model_version=vision_result.get("model_version", "1.0.0"),
            inference_time_ms=vision_result.get("inference_time_ms", 1.0),
            processing_status=vision_result.get("processing_status", "completed"),
            policy_note=vision_result.get("policy_note"),
            is_overridden=False
        )
        db.add(prediction_record)

        # 7. Save Priority Score record
        comps = prio_result["components"]
        prio_record = PriorityScore(
            report_id=report.id,
            severity_component=comps["severity"],
            safety_component=comps["safety"],
            location_risk_component=comps["location_risk"],
            community_impact_component=comps["community_impact"],
            age_component=comps["issue_age"],
            final_score=prio_result["final_score"],
            priority_level=prio_result["priority_level"],
            explanation_json={
                "reasons": prio_result["reasons"],
                "weights": prio_result["weights"],
                "severity_detail": sev_result
            },
            scoring_version=prio_result["scoring_version"]
        )
        db.add(prio_record)

        # 8. Initial audit log
        audit = AuditLog(
            report_id=report.id,
            user_id=citizen_id,
            action="report_submitted",
            previous_state=None,
            new_state={
                "status": "Submitted",
                "category": category.name,
                "ai_predicted_category": suggested_category.name if suggested_category else category.name,
                "confidence": confidence,
                "priority": prio_result["priority_level"]
            },
            notes="Issue report submitted by citizen and processed through AI pipeline."
        )
        db.add(audit)

        # 9. Create notification for citizen
        if citizen_id:
            notif = Notification(
                user_id=citizen_id,
                report_id=report.id,
                title="Report Submitted Successfully",
                message=f"Your civic issue report ({tracking_num}) has been logged with {prio_result['priority_level']} priority.",
                notification_type="report_submitted"
            )
            db.add(notif)

        db.commit()
        db.refresh(report)

        # 10. Snap to OSM road segment
        try:
            from app.services.recurrence_service import RecurrenceService
            seg, _ = RecurrenceService.snap_point_to_segment(db, report.latitude, report.longitude)
            if seg:
                report.road_segment_id = seg.id
                db.commit()
        except Exception:
            pass

        # 11. Run duplicate candidate detection v2
        DuplicateService.find_and_create_duplicate_candidates(db, report)

        return report

    @classmethod
    def update_status(
        cls,
        db: Session,
        report_id: str,
        new_status: str,
        user_id: Optional[str] = None,
        notes: Optional[str] = None,
        resolution_image_url: Optional[str] = None
    ) -> Report:
        """
        Transition report status under strict municipal state machine rules.
        """
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        current = report.status
        allowed = cls.VALID_TRANSITIONS.get(current, [])
        if new_status not in allowed and new_status != current:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from '{current}' to '{new_status}'. Allowed transitions: {allowed}"
            )

        prev_state = {
            "status": current,
            "resolution_notes": report.resolution_notes
        }

        report.status = new_status
        report.updated_at = datetime.now(timezone.utc)
        if notes:
            report.resolution_notes = notes
        if resolution_image_url:
            report.resolution_image_url = resolution_image_url
        if new_status == "Resolved":
            report.resolved_at = datetime.now(timezone.utc)

        # Audit log
        audit = AuditLog(
            report_id=report.id,
            user_id=user_id,
            action="status_change",
            previous_state=prev_state,
            new_state={
                "status": new_status,
                "notes": notes,
                "resolution_image_url": resolution_image_url
            },
            notes=notes or f"Status changed from {current} to {new_status}."
        )
        db.add(audit)

        # Notify citizen
        if report.citizen_id:
            notif = Notification(
                user_id=report.citizen_id,
                report_id=report.id,
                title=f"Report Status Updated: {new_status}",
                message=f"Your issue ({report.tracking_number}) has been updated to {new_status}." + (f" Notes: {notes}" if notes else ""),
                notification_type="status_update"
            )
            db.add(notif)

        db.commit()
        db.refresh(report)
        return report

    @classmethod
    def override_ai_prediction(
        cls,
        db: Session,
        report_id: str,
        user_id: str,
        verified_category_code: Optional[str] = None,
        human_severity: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Report:
        """
        Municipal administrator review and override of AI category or severity.
        Permanently preserves original AI predictions and logs correction.
        """
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        prev_state = {
            "verified_category_id": report.verified_category_id,
            "ai_severity": report.ai_severity,
            "human_severity": report.human_severity,
            "priority_score": report.priority_score,
            "priority_level": report.priority_level
        }

        if verified_category_code:
            v_cat = db.query(Category).filter(Category.code == verified_category_code).first()
            if v_cat:
                report.verified_category_id = v_cat.id
                if report.ai_prediction:
                    report.ai_prediction.is_overridden = True
                    report.ai_prediction.override_category_id = v_cat.id
                    report.ai_prediction.override_user_id = user_id
                    report.ai_prediction.override_notes = notes
                    report.ai_prediction.override_at = datetime.now(timezone.utc)

        if human_severity is not None:
            if not (1 <= human_severity <= 10):
                raise HTTPException(status_code=400, detail="Severity must be between 1 and 10")
            report.human_severity = human_severity

        # Recalculate priority based on human-adjusted parameters
        effective_severity = report.human_severity if report.human_severity is not None else report.ai_severity
        active_cat = report.verified_category or report.category
        prio_result = PriorityService.calculate_priority(
            severity_score=effective_severity,
            category_safety_weight=active_cat.safety_weight if active_cat else 0.5,
            location_text=f"{report.address or ''} {report.area or ''}",
            supporting_reports_count=1,
            created_at=report.created_at
        )

        report.priority_score = prio_result["final_score"]
        report.priority_level = prio_result["priority_level"]
        report.updated_at = datetime.now(timezone.utc)

        # Update or record priority record explanation
        if report.priority_record:
            report.priority_record.final_score = prio_result["final_score"]
            report.priority_record.priority_level = prio_result["priority_level"]
            report.priority_record.explanation_json = {
                "reasons": prio_result["reasons"] + ["Updated following municipal human-in-the-loop review."],
                "weights": prio_result["weights"],
                "human_override_notes": notes
            }

        # Audit log
        audit = AuditLog(
            report_id=report.id,
            user_id=user_id,
            action="ai_override",
            previous_state=prev_state,
            new_state={
                "verified_category_id": report.verified_category_id,
                "human_severity": report.human_severity,
                "recalculated_priority": prio_result["priority_level"],
                "recalculated_score": prio_result["final_score"]
            },
            notes=notes or "Administrator modified AI classification / severity score."
        )
        db.add(audit)
        db.commit()
        db.refresh(report)
        return report

    @classmethod
    def assign_report(
        cls,
        db: Session,
        report_id: str,
        department_id: str,
        staff_id: Optional[str],
        admin_user_id: str,
        notes: Optional[str] = None
    ) -> Report:
        """Assign report to municipal department and personnel."""
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        dept = db.query(Department).filter(Department.id == department_id).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")

        staff_member = None
        if staff_id:
            staff_member = db.query(Staff).filter(Staff.id == staff_id).first()

        assignment = Assignment(
            report_id=report.id,
            department_id=dept.id,
            staff_id=staff_member.id if staff_member else None,
            assigned_by_user_id=admin_user_id,
            notes=notes,
            status="active"
        )
        db.add(assignment)

        # Automatically advance status to 'Assigned' if currently 'Submitted', 'Under Review', or 'Verified'
        if report.status in ["Submitted", "Under Review", "Verified"]:
            report.status = "Assigned"

        report.updated_at = datetime.now(timezone.utc)

        audit = AuditLog(
            report_id=report.id,
            user_id=admin_user_id,
            action="assignment",
            previous_state=None,
            new_state={
                "department": dept.name,
                "staff": staff_member.name if staff_member else "Unassigned",
                "notes": notes
            },
            notes=f"Assigned to {dept.name} ({staff_member.name if staff_member else 'Unassigned personnel'})."
        )
        db.add(audit)
        db.commit()
        db.refresh(report)
        return report
