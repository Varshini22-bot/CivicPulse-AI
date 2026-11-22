import time
from typing import Dict, Any, List, Optional
from app.ml.base import BaseAnalyzer, AnalyzerResult, DetectionBox
from app.ml.heuristic_analyzer import HeuristicAnalyzer
from app.ml.road_defect_detector import RoadDefectDetector
from app.ml.zeroshot_analyzer import ZeroShotAnalyzer
from app.core.config import settings


class CivicVisionPipeline:
    """
    Modular, transparent computer vision pipeline for municipal issue detection.
    Coordinates analyzers under a strict selection policy:
    - The citizen's chosen category is ALWAYS authoritative and never silently overridden.
    - AI provides suggestions with calibrated confidence, bounding boxes, and evidence.
    - Disagreements or low-confidence cases are flagged for human-in-the-loop review.
    """

    def __init__(self):
        self.heuristic_analyzer = HeuristicAnalyzer()
        self.road_detector = RoadDefectDetector()
        self.zeroshot_analyzer = ZeroShotAnalyzer()

    def select_analyzer(
        self,
        image_path: Optional[str],
        citizen_category: str
    ) -> BaseAnalyzer:
        """
        Determines the primary analyzer based on category and local weights availability.
        """
        # If road defect weights are loaded and citizen reported road defect, use detector
        if self.road_detector.is_weights_loaded() and citizen_category in ["pothole", "road_damage"]:
            return self.road_detector

        # If zero-shot CLIP is active and citizen reported non-road category, use zero-shot
        if self.zeroshot_analyzer.clip_model is not None and citizen_category in self.zeroshot_analyzer.CIVIC_PROMPTS:
            return self.zeroshot_analyzer

        # Default standard analyzer: rule-based heuristic baseline
        return self.heuristic_analyzer

    def process_report(
        self,
        image_path: Optional[str],
        description: Optional[str] = "",
        citizen_category_code: str = "other",
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Executes analysis pipeline and applies authoritative citizen selection policy.
        """
        t0 = time.perf_counter()

        # Run primary heuristic analyzer for baseline features and pHash
        heuristic_res = self.heuristic_analyzer.analyze(
            image_path=image_path,
            description=description,
            user_hint=citizen_category_code,
            db=db
        )

        chosen_result: AnalyzerResult = heuristic_res

        # If road detector weights exist and category is a road issue, query detector
        if citizen_category_code in ["pothole", "road_damage"] and self.road_detector.is_weights_loaded():
            det_res = self.road_detector.analyze(
                image_path=image_path,
                description=description,
                user_hint=citizen_category_code,
                db=db
            )
            if det_res.status != "abstain":
                chosen_result = det_res

        # If category is municipal waste/drain/lighting, also evaluate zero-shot
        elif citizen_category_code in self.zeroshot_analyzer.CIVIC_PROMPTS:
            zs_res = self.zeroshot_analyzer.analyze(
                image_path=image_path,
                description=description,
                user_hint=citizen_category_code,
                db=db
            )
            # If zero-shot produced high-confidence suggestion, merge detections/evidence
            if zs_res.status == "ok" and zs_res.confidence > chosen_result.confidence:
                chosen_result = zs_res

        # --- AUTHORITATIVE CITIZEN SELECTION POLICY ---
        # The citizen's chosen category is authoritative. The AI only suggests.
        ai_suggestion = chosen_result.category_suggestion
        ai_confidence = chosen_result.confidence

        is_disagreement = (ai_suggestion != citizen_category_code) and (citizen_category_code != "other")

        if chosen_result.status == "abstain":
            processing_status = "needs_human_verification"
            policy_note = f"AI abstained ({chosen_result.evidence}). Citizen choice '{citizen_category_code}' retained."
        elif is_disagreement:
            if ai_confidence >= 0.70:
                processing_status = "needs_human_verification"
                policy_note = f"AI suggests '{ai_suggestion}' ({ai_confidence:.1%}), differing from citizen '{citizen_category_code}'. Awaiting admin review."
            else:
                processing_status = "needs_human_verification"
                policy_note = f"Low confidence suggestion '{ai_suggestion}' ({ai_confidence:.1%}); citizen choice '{citizen_category_code}' retained."
        else:
            if ai_confidence < 0.40:
                processing_status = "needs_human_verification"
                policy_note = f"Citizen choice '{citizen_category_code}' accepted with low AI confidence ({ai_confidence:.1%})."
            else:
                processing_status = "completed"
                policy_note = f"AI confirmed citizen category '{citizen_category_code}' with {ai_confidence:.1%} confidence."

        total_elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Combine visual features (ensure perceptual hash is preserved from heuristic analyzer)
        detected_features = dict(heuristic_res.detected_features)
        detected_features["analyzer_used"] = chosen_result.analyzer_name
        detected_features["model_version"] = chosen_result.model_version

        return {
            "predicted_category": citizen_category_code,  # Authoritative report category
            "ai_suggested_category": ai_suggestion,
            "confidence": ai_confidence,
            "analyzer_name": chosen_result.analyzer_name,
            "model_version": chosen_result.model_version,
            "processing_status": processing_status,
            "is_disagreement": is_disagreement,
            "policy_note": policy_note,
            "evidence": chosen_result.evidence,
            "detections": [d.to_dict() for d in chosen_result.detections],
            "detection_count": chosen_result.detection_count,
            "relative_box_area": chosen_result.relative_box_area,
            "raw_predictions": chosen_result.raw_predictions,
            "detected_features": detected_features,
            "inference_time_ms": total_elapsed_ms
        }


pipeline = CivicVisionPipeline()
