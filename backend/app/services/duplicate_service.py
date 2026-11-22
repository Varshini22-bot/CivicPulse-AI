import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Report, DuplicateCandidate
from app.core.config import settings

class DuplicateService:
    """
    Geospatial, temporal, semantic, and visual duplicate detection system.
    Evaluates candidate matches and provides explainable composite match percentages
    for municipal decision support.
    """

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Distance in meters between two coordinates."""
        R = 6371000.0  # meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_phi / 2.0)**2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c

    @classmethod
    def evaluate_duplicate_pair(
        cls,
        report_a: Report,
        report_b: Report,
        p_hash_a: Optional[str] = None,
        p_hash_b: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate if report_b is a duplicate candidate of report_a.
        """
        # 1. Geographic distance
        dist_meters = cls.haversine_distance(
            report_a.latitude, report_a.longitude,
            report_b.latitude, report_b.longitude
        )
        
        # Distance score: 0 to 1.0 (1.0 = exact same location, drops off to 0 at 100m)
        if dist_meters <= 15.0:
            dist_score = 1.0
        elif dist_meters <= 50.0:
            dist_score = 0.85
        elif dist_meters <= settings.DUPLICATE_RADIUS_METERS:
            dist_score = max(0.0, 1.0 - (dist_meters / settings.DUPLICATE_RADIUS_METERS))
        else:
            dist_score = 0.0

        # 2. Category matching
        cat_a = report_a.verified_category_id or report_a.category_id
        cat_b = report_b.verified_category_id or report_b.category_id
        is_category_match = (cat_a == cat_b)
        category_score = 1.0 if is_category_match else 0.2

        # 3. Time proximity
        time_a = report_a.created_at
        time_b = report_b.created_at
        if time_a and time_b:
            time_diff_hours = abs((time_a - time_b).total_seconds()) / 3600.0
        else:
            time_diff_hours = 0.0

        if time_diff_hours <= 12.0:
            time_score = 1.0
        elif time_diff_hours <= 72.0:
            time_score = 0.85
        elif time_diff_hours <= (settings.DUPLICATE_TIME_WINDOW_DAYS * 24.0):
            time_score = 0.60
        else:
            time_score = 0.20

        # 4. Visual similarity (Hamming distance on perceptual hashes)
        visual_similarity = 0.5  # Neutral default when no hash
        if p_hash_a and p_hash_b and len(p_hash_a) == len(p_hash_b):
            try:
                # Count matching hex characters
                matches = sum(1 for c1, c2 in zip(p_hash_a, p_hash_b) if c1 == c2)
                visual_similarity = matches / float(len(p_hash_a))
            except Exception:
                visual_similarity = 0.5

        # Weighted composite duplicate score
        # 0.45 Distance + 0.25 Category + 0.15 Time + 0.15 Visual
        composite_score = (
            (0.45 * dist_score) +
            (0.25 * category_score) +
            (0.15 * time_score) +
            (0.15 * visual_similarity)
        )
        composite_score = round(min(1.0, max(0.0, composite_score)), 3)

        reasons = []
        if dist_meters <= 25.0:
            reasons.append(f"Located within {dist_meters:.1f} meters of existing report.")
        elif dist_meters <= 100.0:
            reasons.append(f"Located in immediate vicinity ({dist_meters:.1f}m away).")
            
        if is_category_match:
            reasons.append("Identical civic issue category.")
            
        if time_diff_hours <= 24.0:
            reasons.append(f"Filed within {time_diff_hours:.1f} hours of original report.")
            
        if visual_similarity > 0.70:
            reasons.append("High visual feature similarity in submitted photographs.")

        return {
            "source_report_id": report_a.id,
            "target_report_id": report_b.id,
            "distance_meters": round(dist_meters, 1),
            "category_match": is_category_match,
            "time_diff_hours": round(time_diff_hours, 1),
            "visual_similarity": round(visual_similarity, 2),
            "composite_score": composite_score,
            "match_percentage": int(round(composite_score * 100.0)),
            "is_duplicate_candidate": (composite_score >= settings.DUPLICATE_SCORE_THRESHOLD),
            "reasons": reasons
        }

    @classmethod
    def find_and_create_duplicate_candidates(cls, db: Session, new_report: Report) -> List[DuplicateCandidate]:
        """
        Scan active nearby reports in DB and record duplicate candidate links.
        """
        # Fetch candidate reports within ~150 meters (rough bounding box + exact haversine filter)
        delta_lat = 0.002  # ~220m
        delta_lon = 0.002
        
        candidates = db.query(Report).filter(
            Report.id != new_report.id,
            Report.status.notin_(["Resolved", "Rejected"]),
            Report.latitude.between(new_report.latitude - delta_lat, new_report.latitude + delta_lat),
            Report.longitude.between(new_report.longitude - delta_lon, new_report.longitude + delta_lon)
        ).all()
        
        created_records: List[DuplicateCandidate] = []
        
        # Get hash of new report if available
        new_hash = None
        if new_report.ai_prediction and new_report.ai_prediction.detected_features:
            new_hash = new_report.ai_prediction.detected_features.get("perceptual_hash")

        for existing in candidates:
            exist_hash = None
            if existing.ai_prediction and existing.ai_prediction.detected_features:
                exist_hash = existing.ai_prediction.detected_features.get("perceptual_hash")
                
            eval_result = cls.evaluate_duplicate_pair(new_report, existing, new_hash, exist_hash)
            
            if eval_result["is_duplicate_candidate"]:
                # Check if candidate link already exists
                existing_link = db.query(DuplicateCandidate).filter(
                    ((DuplicateCandidate.source_report_id == new_report.id) & (DuplicateCandidate.target_report_id == existing.id)) |
                    ((DuplicateCandidate.source_report_id == existing.id) & (DuplicateCandidate.target_report_id == new_report.id))
                ).first()
                
                if not existing_link:
                    link = DuplicateCandidate(
                        source_report_id=new_report.id,
                        target_report_id=existing.id,
                        distance_meters=eval_result["distance_meters"],
                        category_match=eval_result["category_match"],
                        time_diff_hours=eval_result["time_diff_hours"],
                        visual_similarity=eval_result["visual_similarity"],
                        composite_score=eval_result["composite_score"],
                        status="suggested",
                        notes="; ".join(eval_result["reasons"])
                    )
                    db.add(link)
                    created_records.append(link)

        if created_records:
            db.commit()
            
        return created_records
