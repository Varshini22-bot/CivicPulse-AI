from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.analytics_service import AnalyticsService
from app.services.export_service import ExportService
from app.ml.evaluation import ModelEvaluator

router = APIRouter(prefix="/analytics", tags=["Analytics & Reporting"])

@router.get("/kpis")
def get_kpis(
    category_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    days: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Real-time municipal KPIs calculated directly from the database."""
    return AnalyticsService.get_overview_kpis(
        db=db,
        category_id=category_id,
        priority=priority,
        area=area,
        days=days
    )

@router.get("/charts")
def get_charts(
    category_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    days: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Aggregated chart datasets for trends, categories, priorities, and areas."""
    return AnalyticsService.get_dashboard_charts(
        db=db,
        category_id=category_id,
        priority=priority,
        area=area,
        days=days
    )

@router.get("/ai-metrics")
def get_ai_metrics():
    """
    Model performance metrics on benchmark civic infrastructure evaluation dataset:
    accuracy, precision, recall, f1-scores, and confusion matrix.
    """
    return ModelEvaluator.compute_evaluation_metrics()

@router.get("/export")
def export_reports_csv(
    category_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Download filtered civic reports dataset as CSV."""
    csv_data = ExportService.generate_csv(
        db=db,
        category_id=category_id,
        priority=priority,
        status=status,
        area=area
    )
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="civicpulse_reports_export.csv"'}
    )
