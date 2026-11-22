from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models import Report, Category
from app.services.geospatial_service import GeospatialService

router = APIRouter(prefix="/map", tags=["Geospatial & Map"])

@router.get("/reports")
def get_map_reports(
    category_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Retrieve geolocated civic issue markers for Leaflet map display.
    Includes coordinates, priority color codes, category icons, and status badges.
    """
    query = db.query(Report)

    if category_id:
        query = query.filter(Report.category_id == category_id)
    if priority:
        query = query.filter(Report.priority_level == priority)
    if status:
        query = query.filter(Report.status == status)
    if area:
        query = query.filter(Report.area == area)

    reports = query.all()

    # Priority color mapping
    priority_colors = {
        "Critical": "#ef4444",  # Red
        "High": "#f97316",      # Orange
        "Medium": "#eab308",    # Yellow
        "Low": "#22c55e"        # Green
    }

    markers = []
    for r in reports:
        markers.append({
            "id": r.id,
            "tracking_number": r.tracking_number,
            "title": r.title,
            "category": r.category.name if r.category else "Unclassified",
            "category_code": r.category.code if r.category else "other",
            "status": r.status,
            "priority_level": r.priority_level,
            "priority_score": r.priority_score,
            "color": priority_colors.get(r.priority_level, "#64748b"),
            "latitude": r.latitude,
            "longitude": r.longitude,
            "address": r.address,
            "area": r.area,
            "is_duplicate": r.is_duplicate,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })

    return markers

@router.get("/hotspots")
def get_map_hotspots(
    eps_meters: float = Query(800.0, ge=100.0, le=5000.0),
    min_samples: int = Query(3, ge=2, le=20),
    db: Session = Depends(get_db)
):
    """
    Detect geographic issue hotspots across municipal wards using DBSCAN spatial density clustering.
    """
    return GeospatialService.detect_hotspots(db=db, eps_meters=eps_meters, min_samples=min_samples)

@router.get("/nearby")
def get_nearby_issues(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius_meters: float = Query(1000.0, ge=50.0, le=10000.0),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Radius search returning reports located within a specified meter threshold.
    """
    return GeospatialService.find_nearby_reports(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius_meters,
        limit=limit
    )
