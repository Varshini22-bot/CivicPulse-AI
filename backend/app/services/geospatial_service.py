import math
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from app.models import Report, Category
from app.services.duplicate_service import DuplicateService
from sklearn.cluster import DBSCAN
import numpy as np

class GeospatialService:
    """
    Spatial intelligence service providing radius queries, geographic hotspot detection,
    and urban density clustering across municipal wards.
    """

    @classmethod
    def find_nearby_reports(
        cls,
        db: Session,
        latitude: float,
        longitude: float,
        radius_meters: float = 1000.0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Find reports within a given radius in meters."""
        # Convert radius in meters to approximate degrees for fast bounding box
        deg_lat = radius_meters / 111000.0
        deg_lon = radius_meters / (111000.0 * math.cos(math.radians(latitude)))

        candidates = db.query(Report).filter(
            Report.latitude.between(latitude - deg_lat, latitude + deg_lat),
            Report.longitude.between(longitude - deg_lon, longitude + deg_lon)
        ).all()

        results = []
        for r in candidates:
            dist = DuplicateService.haversine_distance(latitude, longitude, r.latitude, r.longitude)
            if dist <= radius_meters:
                results.append({
                    "id": r.id,
                    "tracking_number": r.tracking_number,
                    "title": r.title,
                    "category": r.category.name if r.category else "General",
                    "category_code": r.category.code if r.category else "other",
                    "status": r.status,
                    "priority_level": r.priority_level,
                    "priority_score": r.priority_score,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "address": r.address,
                    "distance_meters": round(dist, 1),
                    "created_at": r.created_at.isoformat() if r.created_at else None
                })

        results.sort(key=lambda x: x["distance_meters"])
        return results[:limit]

    @classmethod
    def detect_hotspots(
        cls,
        db: Session,
        eps_meters: float = 800.0,  # ~800 meters neighborhood
        min_samples: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Detect geographic issue hotspots using DBSCAN spatial density clustering on active civic reports.
        """
        # Fetch open issues
        open_reports = db.query(Report).filter(
            Report.status.notin_(["Resolved", "Rejected"])
        ).all()

        if len(open_reports) < min_samples:
            return []

        # Convert lat/lon to radians for spherical DBSCAN with haversine metric
        coords = np.array([[math.radians(r.latitude), math.radians(r.longitude)] for r in open_reports])
        
        # Earth radius in meters
        EARTH_RADIUS = 6371000.0
        eps_radians = eps_meters / EARTH_RADIUS

        dbscan = DBSCAN(eps=eps_radians, min_samples=min_samples, metric="haversine")
        labels = dbscan.fit_predict(coords)

        # Group reports by cluster
        clusters = defaultdict(list)
        for idx, label in enumerate(labels):
            if label != -1:  # Ignore noise points (-1)
                clusters[label].append(open_reports[idx])

        hotspots = []
        for cluster_id, reports in clusters.items():
            lats = [r.latitude for r in reports]
            lngs = [r.longitude for r in reports]
            center_lat = sum(lats) / len(lats)
            center_lng = sum(lngs) / len(lngs)
            
            # Find dominant area name
            areas = [r.area for r in reports if r.area]
            dominant_area = max(set(areas), key=areas.count) if areas else "Urban Sector"
            
            # Category distribution in cluster
            cat_counts = defaultdict(int)
            for r in reports:
                c_name = r.category.name if r.category else "Other"
                cat_counts[c_name] += 1
            dominant_category = max(cat_counts.items(), key=lambda x: x[1])[0]
            
            avg_priority = sum(r.priority_score for r in reports) / len(reports)
            critical_count = sum(1 for r in reports if r.priority_level == "Critical")
            high_count = sum(1 for r in reports if r.priority_level == "High")
            
            # Calculate maximum radius of this cluster in meters
            max_dist = max(DuplicateService.haversine_distance(center_lat, center_lng, r.latitude, r.longitude) for r in reports)
            cluster_radius = max(300.0, round(max_dist, 1))

            urgency = "High" if (critical_count > 0 or avg_priority >= 65.0) else "Moderate"
            
            hotspots.append({
                "hotspot_id": f"HS-BLR-{cluster_id + 1:02d}",
                "area_name": dominant_area,
                "center_latitude": round(center_lat, 6),
                "center_longitude": round(center_lng, 6),
                "radius_meters": cluster_radius,
                "total_reports": len(reports),
                "dominant_category": dominant_category,
                "critical_reports": critical_count,
                "high_priority_reports": high_count,
                "average_priority_score": round(avg_priority, 1),
                "urgency": urgency,
                "insight_summary": f"{dominant_area} exhibits a dense cluster of {len(reports)} active civic issues (primarily {dominant_category}) within a {cluster_radius:.0f}m radius."
            })

        # Sort hotspots by total reports and priority
        hotspots.sort(key=lambda x: (x["critical_reports"] * 2 + x["total_reports"]), reverse=True)
        return hotspots
