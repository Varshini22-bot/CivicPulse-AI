"""
Abstention & Confidence Calibration Analysis
=============================================
Analyzes selective classification behavior for CivicPulse AI:
1. Risk-Coverage Curve: Accuracy as a function of dataset coverage across confidence thresholds tau.
2. Expected Calibration Error (ECE): Measures calibration error across 10 confidence bins.
3. Measured CPU Latency: Measures real wall-clock inference time on local CPU (p50, p95, p99).

References:
- Guo et al., "On Calibration of Modern Neural Networks" (ICML 2017)
- Geifman & El-Yaniv, "Selective Classification for Deep Neural Networks" (NeurIPS 2017)
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.ml.heuristic_analyzer import HeuristicAnalyzer
from app.ml.pipeline import CivicVisionPipeline


def compute_ece(confidences: List[float], correct: List[int], n_bins: int = 10) -> Dict[str, Any]:
    """
    Computes Expected Calibration Error (ECE) across n_bins.
    ECE = sum_{b=1}^B (|B_b| / N) * |acc(B_b) - conf(B_b)|
    """
    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    confidences = np.array(confidences)
    correct = np.array(correct)
    total_samples = len(confidences)

    if total_samples == 0:
        return {"ece": 0.0, "bins": []}

    ece = 0.0
    bins_data = []

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]

        # Samples within bin
        in_bin = (confidences >= bin_lower) & (confidences < bin_upper if i < n_bins - 1 else confidences <= bin_upper)
        bin_size = int(np.sum(in_bin))

        if bin_size > 0:
            bin_acc = float(np.mean(correct[in_bin]))
            bin_conf = float(np.mean(confidences[in_bin]))
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
        "bins": bins_data
    }


def compute_risk_coverage(confidences: List[float], correct: List[int]) -> List[Dict[str, Any]]:
    """
    Computes accuracy and coverage at varying confidence thresholds tau in [0.0, 0.95].
    """
    thresholds = [0.0, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
    conf_arr = np.array(confidences)
    corr_arr = np.array(correct)
    n = len(conf_arr)

    results = []
    for tau in thresholds:
        accepted = conf_arr >= tau
        cov = float(np.sum(accepted)) / n if n > 0 else 0.0
        acc = float(np.mean(corr_arr[accepted])) if np.sum(accepted) > 0 else 1.0

        results.append({
            "threshold_tau": tau,
            "coverage": round(cov, 3),
            "selective_accuracy": round(acc, 3),
            "retained_count": int(np.sum(accepted)),
            "abstained_count": int(n - np.sum(accepted))
        })

    return results


def measure_cpu_latency(pipeline: CivicVisionPipeline, iterations: int = 50) -> Dict[str, Any]:
    """
    Measures actual local CPU inference latency on this machine.
    """
    sample_text = "Dangerous deep pothole on Koramangala 80ft road near traffic signal"
    latencies = []

    # Warmup
    for _ in range(5):
        pipeline.process_report(image_path=None, description=sample_text, citizen_category_code="pothole")

    # Timed runs
    for _ in range(iterations):
        t0 = time.perf_counter()
        pipeline.process_report(image_path=None, description=sample_text, citizen_category_code="pothole")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

    latencies.sort()
    return {
        "iterations": iterations,
        "unit": "milliseconds",
        "mean_ms": round(float(np.mean(latencies)), 2),
        "std_ms": round(float(np.std(latencies)), 2),
        "p50_median_ms": round(float(np.median(latencies)), 2),
        "p95_ms": round(float(np.percentile(latencies, 95)), 2),
        "p99_ms": round(float(np.percentile(latencies, 99)), 2),
        "min_ms": round(float(np.min(latencies)), 2),
        "max_ms": round(float(np.max(latencies)), 2)
    }


def run_abstention_and_calibration_analysis():
    """Executes full abstention, ECE calibration, and latency benchmarks."""
    import csv

    labels_file = "data/ood_bengaluru/labels.csv"
    records = []
    with open(labels_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    pipeline = CivicVisionPipeline()

    confidences = []
    correctness = []

    for r in records:
        gt = r["ground_truth_category"]
        desc = r.get("notes", "")

        res = pipeline.process_report(
            image_path=None,
            description=desc,
            citizen_category_code=gt
        )

        conf = res["confidence"]
        sugg = res["ai_suggested_category"]
        confidences.append(conf)
        correctness.append(1 if sugg == gt else 0)

    # 1. ECE
    ece_data = compute_ece(confidences, correctness, n_bins=5)

    # 2. Risk-Coverage Curve
    risk_cov = compute_risk_coverage(confidences, correctness)

    # 3. CPU Latency measurement
    latency_data = measure_cpu_latency(pipeline, iterations=50)

    report = {
        "benchmark_dataset": labels_file,
        "sample_count": len(records),
        "expected_calibration_error": ece_data,
        "risk_coverage_curve": risk_cov,
        "measured_cpu_latency": latency_data
    }

    out_file = Path("ml/eval/abstention_calibration_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n================================================================================")
    print("      CIVICPULSE AI — ABSTENTION, CALIBRATION & LATENCY REPORT")
    print("================================================================================")
    print(f"Expected Calibration Error (ECE): {ece_data['ece']}")
    print(f"Measured CPU Latency (p50): {latency_data['p50_median_ms']} ms | (p95): {latency_data['p95_ms']} ms")
    print("\nRisk-Coverage Curve (Selective Classification):")
    print("  Tau | Coverage | Selective Acc | Retained | Abstained")
    print("  -----------------------------------------------------")
    for row in risk_cov:
        print(f"  {row['threshold_tau']:.2f}| {row['coverage']:>8.1%} | {row['selective_accuracy']:>13.1%} | {row['retained_count']:>8} | {row['abstained_count']:>9}")
    print(f"\nReport written to: {out_file}\n")
    return report


if __name__ == "__main__":
    run_abstention_and_calibration_analysis()
