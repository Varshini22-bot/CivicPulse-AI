import os
import json
import math
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from app.models import RoadSegment, Report, Category
from app.services.duplicate_service import DuplicateService


class RecurrenceService:
    """
    OpenStreetMap road segment snapping and recurring infrastructure failure intelligence.
    Identifies Chronic Defect Corridors where repeated cosmetic repairs indicate
    systemic subsurface, structural, or drainage failure.
    """

    @classmethod
    def seed_osm_road_network(cls, db: Session, json_path: str = "data/osm/bengaluru_roads.json") -> int:
        """Loads cached Bengaluru road network into the road_segments database table."""
        if not os.path.exists(json_path):
            alt_path = os.path.join("..", json_path)
            if os.path.exists(alt_path):
                json_path = alt_path
            else:
                return 0

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        features = data.get("features", [])
        seeded_count = 0

        for feat in features:
            osm_id = feat.get("osm_way_id")
            existing = db.query(RoadSegment).filter(RoadSegment.osm_id == osm_id).first()
            if not existing:
                seg = RoadSegment(
                    osm_id=osm_id,
                    name=feat.get("name", "Unnamed Road"),
                    highway_type=feat.get("highway_type", "residential"),
                    ward=feat.get("ward"),
                    geometry=feat.get("coordinates", []),
                    length_meters=feat.get("length_meters", 100.0)
                )
                db.add(seg)
                seeded_count += 1

        if seeded_count > 0:
            try:
                db.commit()
            except Exception:
                db.rollback()

        return seeded_count

    @classmethod
    def _point_to_line_segment_distance(
        cls,
        p_lat: float, p_lon: float,
        a_lat: float, a_lon: float,
        b_lat: float, b_lon: float
    ) -> float:
        """
        Computes minimum great-circle distance in meters from point P to line segment AB.
        """
        # Vector AB in planar degree projection
        dx = b_lon - a_lon
        dy = b_lat - a_lat

        if dx == 0.0 and dy == 0.0:
            return DuplicateService.haversine_distance(p_lat, p_lon, a_lat, a_lon)

        # Projection parameter t clamped to [0, 1]
        t = ((p_lon - a_lon) * dx + (p_lat - a_lat) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))

        nearest_lon = a_lon + t * dx
        nearest_lat = a_lat + t * dy

        return DuplicateService.haversine_distance(p_lat, p_lon, nearest_lat, nearest_lon)

    @classmethod
    def snap_point_to_segment(
        cls,
        db: Session,
        latitude: float,
        longitude: float,
        max_snap_meters: float = 60.0
    ) -> Tuple[Optional[RoadSegment], float]:
        """
        Snaps a coordinate to the nearest road segment within max_snap_meters.
        Returns (RoadSegment, distance_in_meters) or (None, infinity).
        """
        segments = db.query(RoadSegment).all()
        if not segments:
            # Attempt auto-seed
            cls.seed_osm_road_network(db)
            segments = db.query(RoadSegment).all()

        best_segment = None
        min_dist = float("inf")

        for seg in segments:
            coords = seg.geometry  # list of [lon, lat]
            if not coords or len(coords) < 2:
                continue

            for i in range(len(coords) - 1):
                a_lon, a_lat = coords[i]
                b_lon, b_lat = coords[i + 1]
                dist = cls._point_to_line_segment_distance(
                    latitude, longitude,
                    a_lat, a_lon,
                    b_lat, b_lon
                )
                if dist < min_dist:
                    min_dist = dist
                    best_segment = seg

        if min_dist <= max_snap_meters:
            return best_segment, min_dist
        return None, min_dist

    @classmethod
    def snap_and_assign_reports(cls, db: Session) -> int:
        """Batch snaps all unsnapped reports to OSM road segments."""
        unsnapped = db.query(Report).filter(Report.road_segment_id.is_(None)).all()
        snapped_count = 0
        for r in unsnapped:
            seg, dist = cls.snap_point_to_segment(db, r.latitude, r.longitude, max_snap_meters=85.0)
            if seg:
                r.road_segment_id = seg.id
                snapped_count += 1
        if snapped_count > 0:
            try:
                db.commit()
            except Exception:
                db.rollback()
        return snapped_count

    @classmethod
    def detect_recurring_failures(
        cls,
        db: Session,
        min_incident_count: int = 3,
        time_window_days: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Identifies recurring infrastructure failures where >= min_incident_count reports
        of the same category occurred on the same road segment within time_window_days.
        Generates civil engineering root-cause advisory recommendations.
        """
        # Ensure reports are snapped
        cls.snap_and_assign_reports(db)

        cutoff = datetime.now(timezone.utc) - timedelta(days=time_window_days)

        # Query reports associated with a road segment
        reports = db.query(Report).filter(
            Report.road_segment_id.isnot(None),
            Report.created_at >= cutoff
        ).all()

        # Group by (road_segment_id, category_id)
        grouped = defaultdict(list)
        for r in reports:
            cat_id = r.verified_category_id or r.category_id
            grouped[(r.road_segment_id, cat_id)].append(r)

        chronic_corridors = []
        for (seg_id, cat_id), report_group in grouped.items():
            if len(report_group) >= min_incident_count:
                seg = report_group[0].road_segment
                cat = report_group[0].category

                cat_name = cat.name if cat else "Civic Defect"
                cat_code = cat.code if cat else "general"
                seg_name = seg.name if seg else "Urban Segment"
                ward_name = seg.ward if (seg and seg.ward) else (report_group[0].area or "BBMP Ward")

                active_count = sum(1 for r in report_group if r.status not in ["Resolved", "Rejected"])
                resolved_count = sum(1 for r in report_group if r.status == "Resolved")
                avg_priority = sum(r.priority_score for r in report_group) / len(report_group)

                # Generate category-specific engineering advisory
                if "pothole" in cat_code or "road" in cat_code:
                    advisory = (
                        f"Repeated road surface failure ({len(report_group)} reports in {time_window_days} days). "
                        "Repeated surface patching indicates sub-base saturation or inadequate storm drain run-off. "
                        "Recommended action: Commission core sample test and inspect roadside gutter alignment."
                    )
                elif "water" in cat_code or "drain" in cat_code:
                    advisory = (
                        f"Repeated water/drainage incident ({len(report_group)} reports in {time_window_days} days). "
                        "Frequent pipe ruptures or drain clogging indicate pipeline hydraulic overload or sediment silting. "
                        "Recommended action: Perform CCTV drain inspection and inspect water main pressure regulator."
                    )
                elif "garbage" in cat_code or "dumping" in cat_code:
                    advisory = (
                        f"Chronic waste accumulation site ({len(report_group)} reports in {time_window_days} days). "
                        "Repeated dumping indicates chronic service frequency shortfall or lack of containment infrastructure. "
                        "Recommended action: Double daily collection frequency and deploy semi-underground waste bins."
                    )
                else:
                    advisory = (
                        f"Repeated {cat_name} recurrence ({len(report_group)} reports in {time_window_days} days). "
                        "Root-cause investigation recommended prior to closing ticket."
                    )

                chronic_corridors.append({
                    "road_segment_id": seg_id,
                    "osm_way_id": seg.osm_id if seg else None,
                    "road_name": seg_name,
                    "highway_type": seg.highway_type if seg else "residential",
                    "ward": ward_name,
                    "category_id": cat_id,
                    "category_name": cat_name,
                    "incident_count": len(report_group),
                    "active_incidents": active_count,
                    "resolved_incidents": resolved_count,
                    "average_priority_score": round(avg_priority, 1),
                    "advisory_recommendation": advisory,
                    "attribution": "Map data © OpenStreetMap contributors, licensed under ODbL 1.0",
                    "sample_tracking_numbers": [r.tracking_number for r in report_group[:5]]
                })

        # Sort by incident count and priority
        chronic_corridors.sort(key=lambda x: (x["incident_count"], x["average_priority_score"]), reverse=True)
        return chronic_corridors
