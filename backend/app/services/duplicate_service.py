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

    @staticmethod
    def hamming_distance_bits(hash_a: str, hash_b: str) -> int:
        """Computes true bitwise Hamming distance between two hex-encoded hash strings."""
        if not hash_a or not hash_b:
            return 9999
        int_a = int(hash_a, 16)
        int_b = int(hash_b, 16)
        xor_val = int_a ^ int_b
        return bin(xor_val).count('1')

    @staticmethod
    def bitwise_hash_similarity(hash_a: Optional[str], hash_b: Optional[str]) -> Optional[float]:
        """
        Returns normalized similarity in [0.0, 1.0] from bitwise Hamming distance.
        Returns None if either hash is missing (never substitutes a fake 0.5 default).
        """
        if not hash_a or not hash_b or len(hash_a) != len(hash_b):
            return None
        total_bits = len(hash_a) * 4  # 4 bits per hex character (e.g. 64 chars = 256 bits)
        if total_bits == 0:
            return None
        dist = DuplicateService.hamming_distance_bits(hash_a, hash_b)
        return max(0.0, min(1.0, 1.0 - (dist / float(total_bits))))

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
        Renormalizes weights when visual features are absent.
        Enforces category-specific distance thresholds.
        """
        # Determine category code for category-specific threshold
        cat_code = (report_a.category.code if report_a.category else None) or "default"
        max_radius = settings.DUPLICATE_CATEGORY_RADII.get(cat_code, settings.DUPLICATE_RADIUS_METERS)

        # 1. Geographic distance
        dist_meters = cls.haversine_distance(
            report_a.latitude, report_a.longitude,
            report_b.latitude, report_b.longitude
        )
        
        # Distance score: 0 to 1.0 based on category-specific radius
        if dist_meters <= 10.0:
            dist_score = 1.0
        elif dist_meters <= max_radius:
            dist_score = max(0.0, 1.0 - (dist_meters / max_radius))
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

        # 4. Visual similarity (Bitwise Hamming distance on perceptual hashes)
        visual_similarity = cls.bitwise_hash_similarity(p_hash_a, p_hash_b)

        # Dynamic weight renormalization:
        # If visual hash is available: 0.45 Dist + 0.25 Cat + 0.15 Time + 0.15 Visual
        # If visual hash is missing: renormalize across Dist, Cat, Time (total 0.85)
        if visual_similarity is not None:
            w_dist = 0.45
            w_cat = 0.25
            w_time = 0.15
            w_vis = 0.15
            composite_score = (
                (w_dist * dist_score) +
                (w_cat * category_score) +
                (w_time * time_score) +
                (w_vis * visual_similarity)
            )
        else:
            # Renormalize without visual component
            base_sum = 0.45 + 0.25 + 0.15  # 0.85
            w_dist = 0.45 / base_sum
            w_cat = 0.25 / base_sum
            w_time = 0.15 / base_sum
            composite_score = (
                (w_dist * dist_score) +
                (w_cat * category_score) +
                (w_time * time_score)
            )

        composite_score = round(min(1.0, max(0.0, composite_score)), 3)

        reasons = []
        if dist_meters <= max_radius:
            reasons.append(f"Located within category-specific radius ({dist_meters:.1f}m / {max_radius:.0f}m max).")
        else:
            reasons.append(f"Distance ({dist_meters:.1f}m) exceeds category threshold of {max_radius:.0f}m.")
            
        if is_category_match:
            reasons.append("Identical civic issue category.")
            
        if time_diff_hours <= 24.0:
            reasons.append(f"Filed within {time_diff_hours:.1f} hours of original report.")
            
        if visual_similarity is not None and visual_similarity > 0.70:
            reasons.append(f"High photographic bitwise similarity ({int(visual_similarity * 100)}%).")

        return {
            "source_report_id": report_a.id,
            "target_report_id": report_b.id,
            "distance_meters": round(dist_meters, 1),
            "category_match": is_category_match,
            "time_diff_hours": round(time_diff_hours, 1),
            "visual_similarity": round(visual_similarity, 2) if visual_similarity is not None else None,
            "composite_score": composite_score,
            "match_percentage": int(round(composite_score * 100.0)),
            "is_duplicate_candidate": (composite_score >= settings.DUPLICATE_SCORE_THRESHOLD and dist_meters <= max_radius),
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
