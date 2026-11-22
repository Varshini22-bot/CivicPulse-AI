"""
Fixture Smoke Test & Out-of-Distribution Evaluation
===================================================
Evaluates the CivicPulse AI Computer Vision analyzers against the 20-sample
Bengaluru fixture smoke test set (data/ood_bengaluru/labels.csv and images).

Data Provenance Disclosure:
---------------------------
- The 20 records in labels.csv and the images in data/ood_bengaluru/images/ are
  reproducible fixture smoke test instances created to verify code paths.
- They are NOT real field photographs submitted by end users.
- Results are reported strictly as "fixture smoke test only, not evidence of performance".

Evaluation Methodology:
-----------------------
- Mode 1: Image-Only (True Classifier Performance).
  Evaluates vision feature extraction and classification without text or hints:
  (image_path=img_path, description="", user_hint=None).
- Mode 2: Multimodal (Assisted Triage Pipeline).
  Evaluates combined image features and citizen description text without label leakage:
  (image_path=img_path, description=desc, user_hint=None).
- Metrics: Top-1 Accuracy with 95% Wilson Score Interval; Macro-F1 with 1,000-sample Bootstrap CI.
"""

import os
import sys
import csv
import math
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.ml.heuristic_analyzer import HeuristicAnalyzer
from app.ml.road_defect_detector import RoadDefectDetector
from app.ml.zeroshot_analyzer import ZeroShotAnalyzer


def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Computes Wilson score interval for binomial proportions."""
    if total == 0:
        return 0.0, 0.0
    z = 1.95996
    p_hat = successes / total
    denom = 1.0 + (z**2) / total
    center = (p_hat + (z**2) / (2 * total)) / denom
    margin = (z / denom) * math.sqrt((p_hat * (1 - p_hat) / total) + (z**2) / (4 * total**2))
    return max(0.0, center - margin), min(1.0, center + margin)


def bootstrap_macro_f1(
    y_true: List[str],
    y_pred: List[str],
    n_iterations: int = 1000,
    seed: int = 42
) -> Tuple[float, Tuple[float, float]]:
    """Computes Macro F1 with 95% bootstrap confidence intervals."""
    from sklearn.metrics import f1_score

    classes = sorted(list(set(y_true + y_pred)))
    eval_classes = [c for c in classes if c != "abstain"]

    if not eval_classes:
        return 0.0, (0.0, 0.0)

    base_f1 = f1_score(y_true, y_pred, labels=eval_classes, average="macro", zero_division=0)

    rng = np.random.RandomState(seed)
    n = len(y_true)
    boot_scores = []

    for _ in range(n_iterations):
        indices = rng.choice(n, size=n, replace=True)
        sample_true = [y_true[i] for i in indices]
        sample_pred = [y_pred[i] for i in indices]
        score = f1_score(sample_true, sample_pred, labels=eval_classes, average="macro", zero_division=0)
        boot_scores.append(score)

    ci_lower = float(np.percentile(boot_scores, 2.5))
    ci_upper = float(np.percentile(boot_scores, 97.5))

    return float(base_f1), (ci_lower, ci_upper)


def run_ood_evaluation(
    labels_csv_path: str = "data/ood_bengaluru/labels.csv",
    images_dir: str = "data/ood_bengaluru/images"
) -> Dict[str, Any]:
    """
    Evaluates analyzers under both Image-Only and Multimodal modes.
    """
    if not os.path.exists(labels_csv_path):
        raise FileNotFoundError(f"OOD labels file not found at: {labels_csv_path}")

    records = []
    with open(labels_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    n_samples = len(records)
    print("\n" + "=" * 80)
    print("      CIVICPULSE AI — FIXTURE SMOKE TEST EVALUATION")
    print("      (Synthetic metadata & fixture images — smoke test only, not evidence of performance)")
    print("=" * 80)
    print(f"Sample Count: N = {n_samples} fixture records")
    print(f"Images Path:  {images_dir}")
    print(f"Confidence Level: 95% Wilson Score Interval (Acc) & 1,000-sample Bootstrap (F1)\n")

    heuristic = HeuristicAnalyzer()
    road_detector = RoadDefectDetector()
    zeroshot = ZeroShotAnalyzer()

    analyzers = [
        ("Heuristic Baseline", heuristic),
        ("Road Defect Detector (RDD2022)", road_detector),
        ("Zero-Shot CLIP (ViT-B/32)", zeroshot)
    ]

    results_table = {
        "evaluation_disclaimer": "Smoke test only, not evidence of performance. Evaluated on synthetic fixture dataset (N=20).",
        "image_only_evaluation": {},
        "multimodal_evaluation": {}
    }

    # =========================================================================
    # MODE 1: IMAGE-ONLY (True Classifier Performance)
    # =========================================================================
    print("--------------------------------------------------------------------------------")
    print(" MODE 1: IMAGE-ONLY EVALUATION (True Visual Classifier Performance)")
    print(" (description='', user_hint=None; no text shortcuts, no label leakage)")
    print("--------------------------------------------------------------------------------")

    for name, analyzer in analyzers:
        y_true = []
        y_pred = []
        abstain_count = 0
        correct_count = 0

        for r in records:
            gt_cat = r["ground_truth_category"]
            img_id = r["image_id"]
            img_path = os.path.join(images_dir, f"{img_id}.jpg") if os.path.exists(os.path.join(images_dir, f"{img_id}.jpg")) else None

            # Execute Image-Only inference (description="", user_hint=None)
            res = analyzer.analyze(image_path=img_path, description="", user_hint=None)

            pred_cat = res.category_suggestion
            if res.status == "abstain":
                abstain_count += 1
                pred_cat = "abstain"

            y_true.append(gt_cat)
            y_pred.append(pred_cat)

            if pred_cat == gt_cat:
                correct_count += 1

        acc = correct_count / n_samples if n_samples > 0 else 0.0
        acc_ci = wilson_score_interval(correct_count, n_samples)
        f1, f1_ci = bootstrap_macro_f1(y_true, y_pred)
        abstain_rate = abstain_count / n_samples if n_samples > 0 else 0.0

        results_table["image_only_evaluation"][name] = {
            "samples": n_samples,
            "correct": correct_count,
            "accuracy": round(acc, 3),
            "accuracy_95ci": [round(acc_ci[0], 3), round(acc_ci[1], 3)],
            "macro_f1": round(f1, 3),
            "macro_f1_95ci": [round(f1_ci[0], 3), round(f1_ci[1], 3)],
            "abstain_count": abstain_count,
            "abstain_rate": round(abstain_rate, 3)
        }

        print(f"[{name}]")
        print(f"  - Accuracy:     {acc:.1%} (95% CI: [{acc_ci[0]:.1%}, {acc_ci[1]:.1%}])")
        print(f"  - Macro F1:     {f1:.3f} (95% CI: [{f1_ci[0]:.3f}, {f1_ci[1]:.3f}])")
        print(f"  - Abstain Rate: {abstain_rate:.1%} ({abstain_count}/{n_samples} reports)\n")

    # =========================================================================
    # MODE 2: MULTIMODAL (Assisted Triage Pipeline: Image + Description Text)
    # =========================================================================
    print("--------------------------------------------------------------------------------")
    print(" MODE 2: MULTIMODAL EVALUATION (Image + Citizen Description Text)")
    print(" (description=citizen_text, user_hint=None; no ground truth hint)")
    print("--------------------------------------------------------------------------------")

    for name, analyzer in analyzers:
        y_true = []
        y_pred = []
        abstain_count = 0
        correct_count = 0

        for r in records:
            gt_cat = r["ground_truth_category"]
            desc = r.get("notes", "")
            img_id = r["image_id"]
            img_path = os.path.join(images_dir, f"{img_id}.jpg") if os.path.exists(os.path.join(images_dir, f"{img_id}.jpg")) else None

            # Execute Multimodal inference with citizen description text, but user_hint=None
            res = analyzer.analyze(image_path=img_path, description=desc, user_hint=None)

            pred_cat = res.category_suggestion
            if res.status == "abstain":
                abstain_count += 1
                pred_cat = "abstain"

            y_true.append(gt_cat)
            y_pred.append(pred_cat)

            if pred_cat == gt_cat:
                correct_count += 1

        acc = correct_count / n_samples if n_samples > 0 else 0.0
        acc_ci = wilson_score_interval(correct_count, n_samples)
        f1, f1_ci = bootstrap_macro_f1(y_true, y_pred)
        abstain_rate = abstain_count / n_samples if n_samples > 0 else 0.0

        results_table["multimodal_evaluation"][name] = {
            "samples": n_samples,
            "correct": correct_count,
            "accuracy": round(acc, 3),
            "accuracy_95ci": [round(acc_ci[0], 3), round(acc_ci[1], 3)],
            "macro_f1": round(f1, 3),
            "macro_f1_95ci": [round(f1_ci[0], 3), round(f1_ci[1], 3)],
            "abstain_count": abstain_count,
            "abstain_rate": round(abstain_rate, 3)
        }

        print(f"[{name}]")
        print(f"  - Accuracy:     {acc:.1%} (95% CI: [{acc_ci[0]:.1%}, {acc_ci[1]:.1%}])")
        print(f"  - Macro F1:     {f1:.3f} (95% CI: [{f1_ci[0]:.3f}, {f1_ci[1]:.3f}])")
        print(f"  - Abstain Rate: {abstain_rate:.1%} ({abstain_count}/{n_samples} reports)\n")

    out_path = Path("ml/eval/ood_benchmark_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results_table, f, indent=2)

    print(f"Detailed smoke test results saved to: {out_path}\n")
    return results_table


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Fixture Smoke Test Evaluation")
    parser.add_argument("--labels", type=str, default="data/ood_bengaluru/labels.csv")
    parser.add_argument("--images", type=str, default="data/ood_bengaluru/images")
    args = parser.parse_args()

    run_ood_evaluation(args.labels, args.images)
