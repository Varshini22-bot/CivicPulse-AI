import os
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Report
from app.services.duplicate_service import DuplicateService
from app.services.embedding_service import EmbeddingService
from app.ml.road_defect_detector import RoadDefectDetector
from app.ml.zeroshot_analyzer import ZeroShotAnalyzer


class ResolutionVerificationService:
    """
    Automated Before-and-After Resolution Verification Engine.
    Audits municipal ticket closures when field officers submit repair completion photographs:
    1. Spatial Proximity: Confirms resolution photo was captured within 50m of original defect.
    2. Scene Consistency: Uses OpenCLIP 512-dim embedding cosine similarity to confirm matching physical background.
    3. Defect Disappearance: Executes vision detector/analyzer on after-photo to confirm defect resolution.
    
    POLICY GUARD:
    Never auto-rejects ticket closure. If verification fails or confidence is low,
    the ticket is resolved provisionally and flagged with 'flagged_for_review' for administrative audit.
    """

    MAX_RESOLUTION_DISTANCE_METERS = 50.0
    MIN_SCENE_SIMILARITY_THRESHOLD = 0.55

    _road_detector: Optional[RoadDefectDetector] = None
    _zeroshot: Optional[ZeroShotAnalyzer] = None

    @classmethod
    def _get_detector(cls) -> RoadDefectDetector:
        if cls._road_detector is None:
            cls._road_detector = RoadDefectDetector()
        return cls._road_detector

    @classmethod
    def _get_zeroshot(cls) -> ZeroShotAnalyzer:
        if cls._zeroshot is None:
            cls._zeroshot = ZeroShotAnalyzer()
        return cls._zeroshot

    @classmethod
    def _resolve_image_disk_path(cls, image_url: Optional[str]) -> Optional[str]:
        if not image_url:
            return None
        if os.path.exists(image_url):
            return image_url
        filename = os.path.basename(image_url)
        for cand in [
            os.path.join("uploads", filename),
            os.path.join("backend", "uploads", filename),
            os.path.join("..", "uploads", filename)
        ]:
            if os.path.exists(cand):
                return cand
        return None

    @classmethod
    def verify_resolution(
        cls,
        db: Session,
        report: Report,
        resolution_image_url: Optional[str],
        resolution_latitude: Optional[float] = None,
        resolution_longitude: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Audits before-and-after photo pair and returns verification payload.
        """
        reasons = []

        # Check if original image exists
        orig_path = cls._resolve_image_disk_path(report.image_url)
        after_path = cls._resolve_image_disk_path(resolution_image_url)

        if not after_path or not orig_path:
            return {
                "status": "unverifiable",
                "verification_score": 0.0,
                "scene_consistency": None,
                "gps_distance_meters": None,
                "defect_disappeared": True,
                "reasons": ["Original report photograph or resolution photograph missing; marked unverifiable."]
            }

        # 1. GPS Distance Check (if resolution coordinates provided)
        dist_meters = None
        gps_score = 1.0
        if resolution_latitude is not None and resolution_longitude is not None:
            dist_meters = DuplicateService.haversine_distance(
                report.latitude, report.longitude,
                resolution_latitude, resolution_longitude
            )
            if dist_meters <= cls.MAX_RESOLUTION_DISTANCE_METERS:
                gps_score = 1.0
                reasons.append(f"GPS verification passed: Resolution photo taken {dist_meters:.1f}m from reported issue.")
            elif dist_meters <= 100.0:
                gps_score = 0.5
                reasons.append(f"GPS caution: Resolution photo taken {dist_meters:.1f}m from reported issue (max {cls.MAX_RESOLUTION_DISTANCE_METERS:.0f}m).")
            else:
                gps_score = 0.0
                reasons.append(f"GPS warning: Resolution photo taken {dist_meters:.1f}m from issue; possible location mismatch.")
        else:
            reasons.append("GPS coordinates for resolution photograph not provided; relying on visual feature matching.")

        # 2. Scene Background Consistency Check (OpenCLIP embeddings)
        zeroshot = cls._get_zeroshot()
        orig_emb = zeroshot.extract_image_embedding(orig_path)
        after_emb = zeroshot.extract_image_embedding(after_path)
        scene_sim = EmbeddingService.cosine_similarity(orig_emb, after_emb)

        if scene_sim is not None:
            if scene_sim >= cls.MIN_SCENE_SIMILARITY_THRESHOLD:
                reasons.append(f"Visual scene consistency confirmed: Background similarity {scene_sim:.1%} (matches original environment).")
            else:
                reasons.append(f"Visual scene divergence: Background similarity {scene_sim:.1%} is below threshold ({cls.MIN_SCENE_SIMILARITY_THRESHOLD:.0%}).")
        else:
            scene_sim = 0.5  # Neutral fallback when embeddings cannot be computed

        # 3. Defect Disappearance Check
        cat_code = (report.category.code if report.category else "pothole") or "pothole"
        defect_disappeared = True

        if "pothole" in cat_code or "road" in cat_code:
            det = cls._get_detector()
            det_res = det.analyze(after_path)
            # If high-confidence defects are still detected in after photo
            if det_res.status == "ok" and det_res.confidence >= 0.50:
                defect_disappeared = False
                reasons.append(f"Persistent defect warning: After-photo still displays active defect ({det_res.confidence:.1%} conf).")
            else:
                reasons.append("Defect disappearance confirmed: No active road defects detected in completion photograph.")
        else:
            zs_res = zeroshot.analyze(after_path)
            if zs_res.status == "ok" and zs_res.confidence >= 0.60 and zs_res.category_suggestion == cat_code:
                defect_disappeared = False
                reasons.append(f"Persistent issue warning: After-photo still displays active {zs_res.category_suggestion}.")
            else:
                reasons.append(f"Defect disappearance confirmed: No active {cat_code.replace('_', ' ')} detected.")

        disappearance_score = 1.0 if defect_disappeared else 0.2

        # 4. Composite Verification Score
        if dist_meters is not None:
            comp_score = (0.35 * gps_score) + (0.35 * scene_sim) + (0.30 * disappearance_score)
        else:
            # Renormalize without GPS
            comp_score = (0.55 * scene_sim) + (0.45 * disappearance_score)

        comp_score = round(float(comp_score), 2)

        if comp_score >= 0.65 and defect_disappeared:
            verif_status = "verified"
            reasons.append("Resolution verified: Completion evidence confirmed.")
        else:
            verif_status = "flagged_for_review"
            reasons.append("Resolution flagged for supervisor audit: Low evidence score or visual divergence.")

        return {
            "status": verif_status,
            "verification_score": comp_score,
            "scene_consistency": round(scene_sim, 2) if scene_sim is not None else None,
            "gps_distance_meters": round(dist_meters, 1) if dist_meters is not None else None,
            "defect_disappeared": defect_disappeared,
            "reasons": reasons
        }
