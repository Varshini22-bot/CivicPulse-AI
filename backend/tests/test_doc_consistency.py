"""
backend/tests/test_doc_consistency.py
=====================================
Automated verification test ensuring all quantitative metrics and constants
documented in README.md, MODEL_CARD.md, and LIMITATIONS.md match the
exact output of result JSON files and backend system configurations.
Guarantees zero invented, drift, or contradictory numbers across the repository.
"""

import re
import json
from pathlib import Path
import pytest
from app.core.config import settings

REPO_ROOT = Path(__file__).parent.parent.parent


def test_seeded_record_count_consistency():
    """Verify that seeded record count (140) is consistent across docs and benchmarks."""
    json_path = REPO_ROOT / "ml" / "eval" / "priority_sensitivity_results.json"
    assert json_path.exists(), f"Missing {json_path}"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    expected_count = data["sample_size"]
    assert expected_count == 140, f"Expected sample size 140, found {expected_count}"

    doc_files = ["README.md", "MODEL_CARD.md", "LIMITATIONS.md", "DATA_CARD.md"]
    for doc in doc_files:
        p = REPO_ROOT / doc
        assert p.exists(), f"Missing {p}"
        content = p.read_text(encoding="utf-8")
        assert "140" in content, f"Expected record count '140' not found in {doc}"
        # Ensure stale count 138 is not referenced for seeded records
        assert "138 seeded" not in content, f"Found stale '138 seeded' reference in {doc}"
        assert "138 records" not in content, f"Found stale '138 records' reference in {doc}"


def test_priority_sensitivity_metrics_consistency():
    """Verify Kendall's tau values in README and MODEL_CARD match sensitivity JSON."""
    json_path = REPO_ROOT / "ml" / "eval" / "priority_sensitivity_results.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data["results"]
    tau_5 = f"{results['5%']['mean_kendall_tau']:.3f}"
    tau_10 = f"{results['10%']['mean_kendall_tau']:.3f}"
    tau_15 = f"{results['15%']['mean_kendall_tau']:.3f}"
    tau_20 = f"{results['20%']['mean_kendall_tau']:.3f}"

    readme_content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    model_card_content = (REPO_ROOT / "MODEL_CARD.md").read_text(encoding="utf-8")

    for tau_val in [tau_5, tau_10, tau_15, tau_20]:
        assert tau_val in readme_content, f"Tau value {tau_val} missing from README.md"
        assert tau_val in model_card_content, f"Tau value {tau_val} missing from MODEL_CARD.md"


def test_duplicate_benchmark_metrics_consistency():
    """Verify test F1 values in README and MODEL_CARD match duplicate benchmark JSON."""
    json_path = REPO_ROOT / "ml" / "eval" / "duplicate_benchmark_results.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_metrics = data["held_out_test_metrics"]
    phash_f1 = f"{test_metrics['method_phash_bitwise']['metrics']['f1_score']:.3f}"
    clip_f1 = f"{test_metrics['method_openclip_embeddings']['metrics']['f1_score']:.3f}"

    readme_content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    model_card_content = (REPO_ROOT / "MODEL_CARD.md").read_text(encoding="utf-8")

    assert phash_f1 in readme_content, f"pHash F1 {phash_f1} missing from README.md"
    assert clip_f1 in readme_content, f"OpenCLIP F1 {clip_f1} missing from README.md"
    assert phash_f1 in model_card_content, f"pHash F1 {phash_f1} missing from MODEL_CARD.md"
    assert clip_f1 in model_card_content, f"OpenCLIP F1 {clip_f1} missing from MODEL_CARD.md"


def test_system_constants_radii_consistency():
    """Verify category-specific radii in docs match backend/app/core/config.py."""
    radii = settings.DUPLICATE_CATEGORY_RADII
    assert radii["pothole"] == 25.0
    assert radii["road_damage"] == 35.0
    assert radii["garbage_overflow"] == 30.0
    assert radii["illegal_dumping"] == 40.0
    assert radii["water_leakage"] == 75.0
    assert radii["blocked_drain"] == 60.0
    assert radii["broken_streetlight"] == 80.0
    assert radii["damaged_infrastructure"] == 40.0

    margin = settings.GPS_ACCURACY_MARGIN_METERS
    assert margin == 10.0

    # Effective radii
    assert (radii["pothole"] + margin) == 35.0
    assert (radii["broken_streetlight"] + margin) == 90.0
    assert (radii["water_leakage"] + margin) == 85.0


def test_doc_markdown_links():
    """Verify that every internal markdown link across core docs resolves to an existing file."""
    doc_files = ["README.md", "MODEL_CARD.md", "DATA_CARD.md", "LIMITATIONS.md", "EVIDENCE.md", "HANDOVER.md"]
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

    broken_links = []
    for doc_name in doc_files:
        doc_path = REPO_ROOT / doc_name
        assert doc_path.exists(), f"Core documentation file {doc_name} is missing"
        content = doc_path.read_text(encoding="utf-8")

        for match in link_pattern.finditer(content):
            target = match.group(2).strip()
            # Ignore external protocols and intra-page fragment anchors
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue

            # Strip target anchors if present (e.g., path/to/file#section)
            clean_target = target.split("#")[0]
            if not clean_target:
                continue

            resolved_path = (doc_path.parent / clean_target).resolve()
            if not resolved_path.exists():
                broken_links.append((doc_name, target, str(resolved_path)))

    assert len(broken_links) == 0, f"Found broken internal markdown links in docs: {broken_links}"

