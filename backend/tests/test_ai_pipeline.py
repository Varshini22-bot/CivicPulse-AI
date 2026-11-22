from app.ml.vision_classifier import classifier
from app.services.severity_service import SeverityService
from app.services.priority_service import PriorityService
from app.services.duplicate_service import DuplicateService
from app.ml.evaluation import ModelEvaluator

def test_vision_classifier_text_heuristics():
    result = classifier.predict(
        image_path=None,
        user_category_hint="garbage_overflow",
        description="Rotting garbage overflowing onto the street with severe foul smell and plastic waste everywhere."
    )
    assert result["predicted_category"] == "garbage_overflow"
    assert result["confidence"] > 0.50
    assert result["processing_status"] == "completed"

def test_severity_estimator_critical_keywords():
    result = SeverityService.estimate_severity(
        category_code="water_leakage",
        confidence=0.88,
        visual_features={"edge_density": 0.12, "dark_pixel_ratio": 0.35},
        description="Major water pipe burst flooding the entire intersection causing dangerous road collapse."
    )
    assert result["severity_score"] >= 8
    assert result["severity_label"] in ["Severe", "Critical"]
    assert "visual_intensity_component" in result
    assert "danger" in result["explanation"] or "rupture" in result["explanation"] or "disruption" in result["explanation"]

def test_priority_service_scoring():
    result = PriorityService.calculate_priority(
        severity_score=9,
        category_safety_weight=0.85,
        location_text="MG Road Metro Junction near Hospital",
        supporting_reports_count=3
    )
    assert result["priority_level"] in ["High", "Critical"]
    assert result["final_score"] >= 70.0
    assert "reasons" in result
    assert len(result["reasons"]) >= 4

def test_duplicate_service_haversine():
    # Distance between two nearby points in Bengaluru (~111 meters apart)
    dist = DuplicateService.haversine_distance(12.9344, 77.6256, 12.9354, 77.6256)
    assert 105.0 <= dist <= 115.0

def test_model_evaluation_pipeline():
    eval_metrics = ModelEvaluator.compute_evaluation_metrics()
    assert eval_metrics["overall_accuracy"] > 0.80
    assert eval_metrics["total_test_samples"] > 25
    assert len(eval_metrics["classes"]) == 8
    assert "pothole" in eval_metrics["per_class_metrics"]
    assert len(eval_metrics["confusion_matrix"]) == 8
