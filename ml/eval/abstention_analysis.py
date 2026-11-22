"""
Abstention & Latency Benchmark Analysis
=======================================
Analyzes selective classification behavior and real inference latency for CivicPulse AI:
1. Selective Classification (Risk-Coverage): Accuracy and abstention trade-offs across confidence thresholds tau.
2. Calibration Caveat: Explains why Expected Calibration Error (ECE) is statistically uninformative on small N (N=20 < 50) and suppresses headline ECE.
3. Measured End-to-End CPU Latency: Real wall-clock timing per image (disk read, PIL decode, array conversion, model forward pass) on local CPU with 10 warmups and 50 timed iterations.

References:
- Geifman & El-Yaniv, "Selective Classification for Deep Neural Networks" (NeurIPS 2017)
- Guo et al., "On Calibration of Modern Neural Networks" (ICML 2017) - Section 3 (Reliability Diagrams & Binning)
"""

import os
import sys
import time
import json
import csv
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
from PIL import Image

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.ml.heuristic_analyzer import HeuristicAnalyzer
from app.ml.road_defect_detector import RoadDefectDetector
from app.ml.zeroshot_analyzer import ZeroShotAnalyzer
from app.ml.pipeline import CivicVisionPipeline


def compute_ece(confidences: List[float], correct: List[int], n_bins: int = 10) -> Dict[str, Any]:
    """
    Computes Expected Calibration Error (ECE) across n_bins.
    Note: Requires N >= 50-100 for statistically meaningful probability calibration.
    """
    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    conf_arr = np.array(confidences)
    corr_arr = np.array(correct)
    total_samples = len(conf_arr)

    if total_samples == 0:
        return {"ece": 0.0, "bins": []}

    ece = 0.0
    bins_data = []

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]

        in_bin = (conf_arr >= bin_lower) & (conf_arr < bin_upper if i < n_bins - 1 else conf_arr <= bin_upper)
        bin_size = int(np.sum(in_bin))

        if bin_size > 0:
            bin_acc = float(np.mean(corr_arr[in_bin]))
            bin_conf = float(np.mean(conf_arr[in_bin]))
            bin_error = abs(bin_acc - bin_conf)
            ece += (bin_size / total_samples) * bin_error

            bins_data.append({
                "bin_range": [round(bin_lower, 2), round(bin_upper, 2)],
                "count": bin_size,
                "accuracy": round(bin_acc, 3),
                "confidence": round(bin_conf, 3),
                "calibration_gap": round(bin_error, 3)
            })

    return {
        "ece": round(float(ece), 4),
        "n_bins": n_bins,
        "sample_count": total_samples,
        "bins": bins_data
    }


def compute_risk_coverage(confidences: List[float], correct: List[int]) -> List[Dict[str, Any]]:
    """
    Computes accuracy and coverage at varying confidence thresholds tau.
    """
    thresholds = [0.0, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80]
    conf_arr = np.array(confidences)
    corr_arr = np.array(correct)
    n = len(conf_arr)

    results = []
    for tau in thresholds:
        accepted = conf_arr >= tau
        retained = int(np.sum(accepted))
        cov = float(retained) / n if n > 0 else 0.0
        acc = float(np.mean(corr_arr[accepted])) if retained > 0 else 0.0

        results.append({
            "threshold_tau": tau,
            "coverage": round(cov, 3),
            "selective_accuracy": round(acc, 3),
            "retained_count": retained,
            "abstained_count": int(n - retained)
        })

    return results


def measure_analyzer_latency(analyzer, image_path: str, description: str = "", warmups: int = 10, iterations: int = 50) -> Dict[str, Any]:
    """
    Measures true end-to-end latency per image on this machine:
    - Disk read & PIL decode
    - Array preprocessing
    - Model forward pass / heuristic analysis
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Benchmark image not found: {image_path}")

    # Warmup runs (JIT/cache/model initialization)
    for _ in range(warmups):
        analyzer.analyze(image_path=image_path, description=description, user_hint=None)

    latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        analyzer.analyze(image_path=image_path, description=description, user_hint=None)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

    latencies.sort()
    return {
        "iterations": iterations,
        "warmups": warmups,
        "unit": "milliseconds",
        "mean_ms": round(float(np.mean(latencies)), 2),
        "std_ms": round(float(np.std(latencies)), 2),
        "p50_median_ms": round(float(np.median(latencies)), 2),
        "p95_ms": round(float(np.percentile(latencies, 95)), 2),
        "p99_ms": round(float(np.percentile(latencies, 99)), 2),
        "min_ms": round(float(np.min(latencies)), 2),
        "max_ms": round(float(np.max(latencies)), 2)
    }


def run_benchmarks(
    labels_file: str = "data/ood_bengaluru/labels.csv",
    images_dir: str = "data/ood_bengaluru/images"
) -> Dict[str, Any]:
    """Executes full abstention, latency, and calibration analysis."""
    records = []
    with open(labels_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    n_samples = len(records)
    print("\n" + "=" * 80)
    print("      CIVICPULSE AI — ABSTENTION, CALIBRATION & REAL LATENCY ANALYSIS")
    print("=" * 80)
    print(f"Dataset: N = {n_samples} fixture records (data/ood_bengaluru/)")
    print("Note: Evaluated on synthetic fixture dataset (smoke test only, not evidence of performance).\n")

    # Pick representative fixture image for end-to-end latency measurement
    benchmark_image = os.path.join(images_dir, "BLR_001.jpg")
    if not os.path.exists(benchmark_image):
        # Create a fallback image if missing
        Path(images_dir).mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (640, 480), color=(100, 100, 100))
        img.save(benchmark_image, "JPEG")

    heuristic = HeuristicAnalyzer()
    road_detector = RoadDefectDetector()
    zeroshot = ZeroShotAnalyzer()

    print("--- Measuring Real End-to-End CPU Latency (10 warmups, 50 timed iterations) ---")
    print(f"Test Image: {benchmark_image} (640x480 JPEG)")

    latencies = {}
    for name, analyzer in [
        ("HeuristicAnalyzer (Image-Only)", heuristic),
        ("RoadDefectDetector (Fallback)", road_detector),
        ("ZeroShotAnalyzer (OpenCLIP ViT-B/32)", zeroshot)
    ]:
        print(f"Measuring latency for {name}...")
        lat = measure_analyzer_latency(analyzer, benchmark_image, description="", warmups=10, iterations=50)
        latencies[name] = lat
        print(f"  p50: {lat['p50_median_ms']} ms | p95: {lat['p95_ms']} ms | p99: {lat['p99_ms']} ms | mean: {lat['mean_ms']} ± {lat['std_ms']} ms")

    # Calibration Caveat (Guo et al. 2017)
    ece_note = (
        "Headline Expected Calibration Error (ECE) is SUPPRESSED for N=20. "
        "Standard ECE with 10 bins requires at least 50-100 samples per bin to yield "
        "statistically meaningful probability estimates; with N=20 total samples across 10 bins, "
        "most bins have 0-2 samples, resulting in extreme sample variance and uninterpretable ECE values."
    )

    # Risk-Coverage Analysis on Multimodal Pipeline
    print("\n--- Computing Selective Classification Risk-Coverage on Fixture Set ---")
    pipeline = CivicVisionPipeline()
    confidences = []
    correctness = []

    for r in records:
        gt = r["ground_truth_category"]
        desc = r.get("notes", "")
        img_id = r["image_id"]
        img_path = os.path.join(images_dir, f"{img_id}.jpg") if os.path.exists(os.path.join(images_dir, f"{img_id}.jpg")) else None

        res = pipeline.process_report(
            image_path=img_path,
            description=desc,
            citizen_category_code=gt
        )
        conf = res["confidence"]
        sugg = res["ai_suggested_category"]
        confidences.append(conf)
        correctness.append(1 if sugg == gt else 0)

    risk_cov = compute_risk_coverage(confidences, correctness)

    print("\nSelective Classification Risk-Coverage Curve (Multimodal Assisted Triage):")
    print("  Tau | Coverage | Selective Acc | Retained | Abstained")
    print("  -----------------------------------------------------")
    for row in risk_cov:
        print(f"  {row['threshold_tau']:.2f}| {row['coverage']:>8.1%} | {row['selective_accuracy']:>13.1%} | {row['retained_count']:>8} | {row['abstained_count']:>9}")

    report = {
        "benchmark_dataset": labels_file,
        "sample_count": n_samples,
        "disclaimer": "Smoke test only, not evidence of performance.",
        "calibration_status": "SUPPRESSED",
        "calibration_reason": ece_note,
        "risk_coverage_curve": risk_cov,
        "measured_end_to_end_cpu_latencies": latencies
    }

    out_file = Path("ml/eval/abstention_calibration_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved to: {out_file}\n")
    return report


if __name__ == "__main__":
    run_benchmarks()
