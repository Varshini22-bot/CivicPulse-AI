import os
import sys
import math
from datetime import datetime, timedelta, timezone
import pytest

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.services.priority_service import PriorityService
from ml.eval.priority_sensitivity import run_priority_sensitivity_analysis


def test_continuous_saturating_age_monotonicity():
    """Verify that age scoring is smooth, continuous, and strictly monotonic."""
    now = datetime.now(timezone.utc)

    # 0 hours -> 0.0
    _, score_0h = PriorityService.compute_continuous_age_score(now)
    assert score_0h == 0.0

    # 12 hours -> ~15
    _, score_12h = PriorityService.compute_continuous_age_score(now - timedelta(hours=12))
    assert 14.0 <= score_12h <= 17.0

    # 24 hours (1 day) -> ~28
    _, score_24h = PriorityService.compute_continuous_age_score(now - timedelta(hours=24))
    assert 26.0 <= score_24h <= 30.0

    # 72 hours (3 days) -> ~63 (1 - e^-1)
    _, score_72h = PriorityService.compute_continuous_age_score(now - timedelta(hours=72))
    assert 61.0 <= score_72h <= 65.0

    # 168 hours (7 days) -> ~90
    _, score_168h = PriorityService.compute_continuous_age_score(now - timedelta(hours=168))
    assert 88.0 <= score_168h <= 92.0

    # Strict monotonicity check
    assert score_0h < score_12h < score_24h < score_72h < score_168h


def test_osm_poi_location_risk_calculation():
    """Verify that proximity to real OpenStreetMap POIs elevates location risk."""
    # Coordinate near St. John's Medical College Hospital (lat 12.9315, lon 77.6210)
    score, reasons, matched = PriorityService.compute_location_risk(
        latitude=12.9316,
        longitude=77.6212,
        location_text=""
    )
    assert score >= 60.0  # Elevated above base 35
    assert len(matched) > 0
    assert matched[0]["category"] == "hospital"
    assert any("OSM Proximity" in r for r in reasons)


def test_location_risk_keyword_fallback():
    """Verify fallback to address keyword matching when coordinates are absent."""
    score, reasons, matched = PriorityService.compute_location_risk(
        latitude=None,
        longitude=None,
        location_text="10th Main Road, near Apollo Hospital"
    )
    assert score == 85.0
    assert any("hospital" in r.lower() for r in reasons)


def test_priority_sensitivity_benchmark_executes_cleanly():
    """Smoke test ensuring Monte Carlo sensitivity analysis runs and outputs valid Kendall's tau."""
    res = run_priority_sensitivity_analysis(sample_size=30, n_iterations=20, seed=42)
    assert "results" in res
    assert "10%" in res["results"]
    tau_10 = res["results"]["10%"]["mean_kendall_tau"]
    assert 0.80 <= tau_10 <= 1.00
    assert res["results"]["10%"]["rank_stability"] in ["High", "Very High"]
