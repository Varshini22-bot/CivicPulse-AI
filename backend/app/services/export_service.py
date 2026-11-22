import io
import csv
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Report

class ExportService:
    """
    Exports municipal civic reports in CSV format with configurable filtering.
    """

    @classmethod
    def generate_csv(
        cls,
        db: Session,
        category_id: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        area: Optional[str] = None
    ) -> str:
        query = db.query(Report)
        if category_id:
            query = query.filter(Report.category_id == category_id)
        if priority:
            query = query.filter(Report.priority_level == priority)
        if status:
            query = query.filter(Report.status == status)
        if area:
            query = query.filter(Report.area == area)

        reports = query.order_by(Report.created_at.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            "Tracking Number",
            "Title",
            "Category",
            "Verified Category",
            "Status",
            "Priority Level",
            "Priority Score",
            "AI Severity",
            "Human Severity",
            "Latitude",
            "Longitude",
            "Address",
            "Area",
            "Is Duplicate",
            "Created Date",
            "Resolved Date",
            "Resolution Notes"
        ])

        for r in reports:
            writer.writerow([
                r.tracking_number,
                r.title,
                r.category.name if r.category else "",
                r.verified_category.name if r.verified_category else "",
                r.status,
                r.priority_level,
                r.priority_score,
                r.ai_severity,
                r.human_severity or "",
                r.latitude,
                r.longitude,
                r.address or "",
                r.area or "",
                "Yes" if r.is_duplicate else "No",
                r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
                r.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if r.resolved_at else "",
                r.resolution_notes or ""
            ])

        return output.getvalue()
