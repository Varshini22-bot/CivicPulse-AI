import os
import io
import sys
from pathlib import Path
import pytest
from PIL import Image

# Ensure project root is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.ml.base import BaseAnalyzer, AnalyzerResult, DetectionBox
from app.ml.heuristic_analyzer import HeuristicAnalyzer
from app.ml.road_defect_detector import RoadDefectDetector
from app.ml.zeroshot_analyzer import ZeroShotAnalyzer
from app.ml.pipeline import CivicVisionPipeline
from app.services.severity_service import SeverityService
from app.services.report_service import ReportService
from app.database.connection import SessionLocal
from app.models import Report, Category, AIPrediction


def test_base_analyzer_contract():
    """All analyzers must conform to the BaseAnalyzer interface and return AnalyzerResult."""
    heuristic = HeuristicAnalyzer()
    road_detector = RoadDefectDetector()
    zeroshot = ZeroShotAnalyzer()

    for analyzer in [heuristic, road_detector, zeroshot]:
        assert isinstance(analyzer, BaseAnalyzer)
        result = analyzer.analyze(image_path=None, description="Test description", user_hint="pothole")
        assert isinstance(result, AnalyzerResult)
        assert isinstance(result.analyzer_name, str)
        assert isinstance(result.model_version, str)
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0
        assert result.status in ["ok", "low_confidence", "abstain"]
        assert isinstance(result.detections, list)


def test_road_defect_detector_honest_abstention_without_weights():
    """Road defect detector must abstain honestly when weights file does not exist locally."""
    detector = RoadDefectDetector(model_path="backend/app/ml/weights/non_existent_weights.onnx")
    assert not detector.is_weights_loaded()

    result = detector.analyze(image_path=None, description="pothole on road", user_hint="pothole")
    assert result.status == "abstain"
    assert "weights not found" in result.evidence.lower()
    assert result.confidence == 0.0
    assert len(result.detections) == 0


def test_zeroshot_analyzer_abstention_on_missing_image():
    """Zero-shot CLIP analyzer must abstain when no image is provided."""
    analyzer = ZeroShotAnalyzer()
    result = analyzer.analyze(image_path=None, description="Garbage pile", user_hint="garbage_overflow")
    assert result.status == "abstain"
    assert "No image provided" in result.evidence


def test_authoritative_citizen_selection_policy():
    """
    Authoritative citizen selection policy:
    1. The citizen's chosen category is NEVER changed in predicted_category.
    2. AI only provides a suggestion (ai_suggested_category).
    3. High-confidence disagreement marks report as 'needs_human_verification'.
    """
    pipeline = CivicVisionPipeline()

    # Case 1: Citizen reports 'garbage_overflow', text strongly hints 'pothole'
    result = pipeline.process_report(
        image_path=None,
        description="Deep asphalt crater cavity bike fell into hole",
        citizen_category_code="garbage_overflow"
    )

    # Citizen choice is authoritative
    assert result["predicted_category"] == "garbage_overflow"
    assert result["ai_suggested_category"] == "pothole"
    assert result["is_disagreement"] is True
    assert result["processing_status"] == "needs_human_verification"
    assert "AI suggests 'pothole'" in result["policy_note"]
    assert "differing from citizen 'garbage_overflow'" in result["policy_note"]


def test_severity_estimation_with_detection_box_metrics():
    """
    Severity service accepts optional detection_count and relative_box_area,
    adjusting severity within the 1-10 bounded scale without cm depth claims.
    """
    db = SessionLocal()
    try:
        # Baseline severity for pothole with no detections
        sev_base = SeverityService.estimate_severity(
            category_code="pothole",
            confidence=0.8,
            visual_features={},
            description="Pothole on asphalt road",
            db=db
        )
        score_base = sev_base["severity_score"]

        # Severity with large detected defect (occupying 25% of image area)
        sev_detected = SeverityService.estimate_severity(
            category_code="pothole",
            confidence=0.8,
            visual_features={},
            description="Pothole on asphalt road",
            db=db,
            detection_count=2,
            relative_box_area=0.25
        )
        score_detected = sev_detected["severity_score"]

        assert 1 <= score_detected <= 10
        assert score_detected >= score_base
        assert "detection_metrics" in sev_detected
        assert sev_detected["detection_metrics"]["relative_box_area"] == 0.25
        assert sev_detected["detection_metrics"]["scale_note"] == "Estimated from relative defect area; no real-world physical scale."
    finally:
        db.close()


def test_ai_prediction_persistence_and_admin_feedback_loop(client, admin_token):
    """
    Submitting a report stores full AI prediction details.
    When an admin overrides the AI decision, feedback labels are stored for model retraining export.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Submit report
    res = client.post(
        "/api/reports",
        data={
            "title": "Road crater on Indiranagar 100ft road",
            "description": "Large asphalt crater cavity posing severe bike skidding hazard",
            "category_code": "pothole",
            "latitude": 12.9716,
            "longitude": 77.6412,
            "address": "100ft Road Indiranagar",
            "area": "Indiranagar"
        }
    )
    assert res.status_code == 201
    report_data = res.json()
    report_id = report_data["id"]

    # 2. Get report detail
    detail_res = client.get(f"/api/reports/{report_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    ai_pred = detail["ai_prediction"]
    assert ai_pred is not None
    assert "model_name" in ai_pred
    assert "processing_status" in ai_pred
    assert ai_pred["is_overridden"] is False
    assert "detections" in ai_pred

    # 3. Admin override
    override_res = client.post(
        f"/api/admin/reports/{report_id}/override",
        headers=headers,
        json={
            "verified_category_code": "road_damage",
            "human_severity": 8,
            "notes": "Reclassified from pothole to general asphalt structural road damage."
        }
    )
    assert override_res.status_code == 200
    updated_detail = override_res.json()
    assert updated_detail["verified_category"] == "Road Damage"

    # Verify AI prediction record retained feedback for retraining
    updated_pred = updated_detail["ai_prediction"]
    assert updated_pred["is_overridden"] is True
    assert updated_pred["override_category_code"] == "road_damage"


def test_ml_evaluation_scripts_execute_cleanly():
    """Smoke test ensuring detector, OOD benchmark, and calibration scripts run without exception."""
    from ml.eval.evaluate_detector import run_detector_evaluation
    from ml.eval.evaluate_ood import run_ood_evaluation
    from ml.eval.abstention_analysis import compute_ece, compute_risk_coverage

    # 1. Detector evaluation mock smoke test
    det_res = run_detector_evaluation(model_path="non_existent.onnx")
    assert det_res["status"] == "mock_smoke_test_passed"
    assert "map_50" in det_res

    # 2. OOD benchmark execution
    ood_res = run_ood_evaluation(labels_csv_path="data/ood_bengaluru/labels.csv")
    assert "image_only_evaluation" in ood_res
    assert "multimodal_evaluation" in ood_res
    assert "Heuristic Baseline" in ood_res["image_only_evaluation"]
    assert "Road Defect Detector (RDD2022)" in ood_res["image_only_evaluation"]
    assert ood_res["image_only_evaluation"]["Road Defect Detector (RDD2022)"]["abstain_rate"] == 1.0

    # 3. Calibration ECE & risk coverage math verification
    confidences = [0.9, 0.8, 0.4, 0.35, 0.2]
    correct = [1, 1, 0, 0, 0]
    ece_data = compute_ece(confidences, correct, n_bins=5)
    assert 0.0 <= ece_data["ece"] <= 1.0

    risk_cov = compute_risk_coverage(confidences, correct)
    assert len(risk_cov) > 0
    assert risk_cov[0]["threshold_tau"] == 0.0
    assert risk_cov[0]["coverage"] == 1.0

