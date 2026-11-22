import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from app.models import Report, Category
from app.services.duplicate_service import DuplicateService
from app.core.config import settings
from sklearn.cluster import DBSCAN, HDBSCAN
import numpy as np

class GeospatialService:
    """
    Spatial intelligence service providing radius queries, geographic hotspot detection,
    and urban density clustering across municipal wards.
    Supports both fixed-radius DBSCAN and hierarchical HDBSCAN with temporal decay weighting.
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
        algorithm: str = "hdbscan",
        eps_meters: Optional[float] = None,
        min_samples: Optional[int] = None,
        min_cluster_size: Optional[int] = None,
        category_code: Optional[str] = None,
        time_decay_half_life_days: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect geographic issue hotspots using spatial density clustering on active civic reports.
        Supports both HDBSCAN (hierarchical variable-density) and DBSCAN (fixed-radius).
        Applies exponential temporal decay weighting to prioritize recently active clusters.
        """
        if eps_meters is None:
            eps_meters = settings.DBSCAN_EPS_METERS
        if min_samples is None:
            min_samples = settings.HDBSCAN_MIN_SAMPLES if algorithm.lower() == "hdbscan" else settings.DBSCAN_MIN_SAMPLES
        if min_cluster_size is None:
            min_cluster_size = settings.HDBSCAN_MIN_CLUSTER_SIZE
        if time_decay_half_life_days is None:
            time_decay_half_life_days = settings.HOTSPOT_TIME_DECAY_HALF_LIFE_DAYS

        query = db.query(Report).filter(
            Report.status.notin_(["Resolved", "Rejected"])
        )

        if category_code:
            query = query.join(Report.category).filter(Category.code == category_code)

        open_reports = query.all()

        required_min = min_cluster_size if algorithm.lower() == "hdbscan" else min_samples
        if len(open_reports) < required_min:
            return []

        # Convert lat/lon to radians for spherical haversine metric
        coords = np.array([[math.radians(r.latitude), math.radians(r.longitude)] for r in open_reports])
        EARTH_RADIUS = 6371000.0

        if algorithm.lower() == "hdbscan":
            clusterer = HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=min_samples,
                metric="haversine",
                copy=True
            )
            labels = clusterer.fit_predict(coords)
            probabilities = getattr(clusterer, "probabilities_", [1.0] * len(open_reports))
        else:
            eps_radians = eps_meters / EARTH_RADIUS
            dbscan = DBSCAN(eps=eps_radians, min_samples=min_samples, metric="haversine")
            labels = dbscan.fit_predict(coords)
            probabilities = [1.0] * len(open_reports)

        # Group reports by cluster
        clusters = defaultdict(list)
        cluster_probs = defaultdict(list)
        for idx, label in enumerate(labels):
            if label != -1:  # Ignore noise points (-1)
                clusters[label].append(open_reports[idx])
                cluster_probs[label].append(float(probabilities[idx]))

        now = datetime.now(timezone.utc)
        decay_lambda = math.log(2.0) / max(1.0, time_decay_half_life_days)

        hotspots = []
        for cluster_id, reports in clusters.items():
            lats = [r.latitude for r in reports]
            lngs = [r.longitude for r in reports]
            center_lat = sum(lats) / len(lats)
            center_lng = sum(lngs) / len(lngs)
            
            areas = [r.area for r in reports if r.area]
            dominant_area = max(set(areas), key=areas.count) if areas else "Urban Sector"
            
            cat_counts = defaultdict(int)
            for r in reports:
                c_name = r.category.name if r.category else "Other"
                cat_counts[c_name] += 1
            dominant_category = max(cat_counts.items(), key=lambda x: x[1])[0]
            
            avg_priority = sum(r.priority_score for r in reports) / len(reports)
            critical_count = sum(1 for r in reports if r.priority_level == "Critical")
            high_count = sum(1 for r in reports if r.priority_level == "High")
            
            # Temporal decay score: recent issues count more heavily
            temporal_weights = []
            for r in reports:
                r_time = r.created_at
                if r_time:
                    if r_time.tzinfo is None:
                        r_time = r_time.replace(tzinfo=timezone.utc)
                    age_days = max(0.0, (now - r_time).total_seconds() / 86400.0)
                else:
                    age_days = 0.0
                w = math.exp(-decay_lambda * age_days)
                temporal_weights.append(w)

            temporal_weighted_activity = sum(temporal_weights)
            mean_cluster_membership = float(np.mean(cluster_probs[cluster_id])) if cluster_probs[cluster_id] else 1.0

            max_dist = max(DuplicateService.haversine_distance(center_lat, center_lng, r.latitude, r.longitude) for r in reports)
            cluster_radius = max(100.0, round(max_dist, 1))

            urgency = "High" if (critical_count > 0 or avg_priority >= 65.0) else "Moderate"
            
            hotspots.append({
                "hotspot_id": f"HS-BLR-{cluster_id + 1:02d}",
                "algorithm": algorithm.lower(),
                "area_name": dominant_area,
                "center_latitude": round(center_lat, 6),
                "center_longitude": round(center_lng, 6),
                "radius_meters": cluster_radius,
                "total_reports": len(reports),
                "temporal_weighted_activity": round(temporal_weighted_activity, 2),
                "cluster_stability_score": round(mean_cluster_membership, 3),
                "dominant_category": dominant_category,
                "critical_reports": critical_count,
                "high_priority_reports": high_count,
                "average_priority_score": round(avg_priority, 1),
                "urgency": urgency,
                "insight_summary": f"{dominant_area} exhibits a dense {algorithm.upper()} cluster of {len(reports)} active issues (primarily {dominant_category}) within a {cluster_radius:.0f}m radius."
            })

        hotspots.sort(key=lambda x: (x["critical_reports"] * 2 + x["temporal_weighted_activity"]), reverse=True)
        return hotspots
