"""
Duplicate Detection Benchmark: Bitwise pHash vs. OpenCLIP Image Embeddings
==========================================================================
Evaluates visual similarity techniques on augmentation-derived image pairs:
1. Method A: Perceptual Hash (64-bit dHash / pHash with bitwise Hamming distance).
2. Method B: OpenCLIP ViT-B/32 Cosine Similarity.
3. Method C: Composite Spatial-Semantic-Visual Duplicate Gate.

DISCLAIMER & METHODOLOGY NOTE:
-----------------------------
This script conducts an *optimistic synthetic evaluation* using image augmentations
(random crops, perspective warping, brightness shifts, compression) to simulate
different citizen smartphone photos of the same physical civic defect.
It does NOT substitute for a real-world annotated duplicate benchmark.
Results are reported with 95% Bootstrap Confidence Intervals.
"""

import os
import sys
import time
import json
import random
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
from PIL import Image, ImageEnhance, ImageOps

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.services.duplicate_service import DuplicateService
from app.services.embedding_service import EmbeddingService
from app.ml.heuristic_analyzer import HeuristicAnalyzer
from app.ml.zeroshot_analyzer import ZeroShotAnalyzer


def apply_citizen_photo_augmentations(img: Image.Image, seed: int = 42) -> Image.Image:
    """
    Simulates variations in citizen mobile captures:
    - Slight crop & re-scale (perspective / framing shift)
    - Exposure / brightness adjustment
    - Slight rotation (unsteady handheld camera)
    """
    rng = random.Random(seed)
    w, h = img.size

    # 1. Random crop (5-12%)
    crop_pct = rng.uniform(0.05, 0.12)
    left = int(w * crop_pct * rng.uniform(0.0, 0.5))
    top = int(h * crop_pct * rng.uniform(0.0, 0.5))
    right = int(w - (w * crop_pct * rng.uniform(0.5, 1.0)))
    bottom = int(h - (h * crop_pct * rng.uniform(0.5, 1.0)))
    cropped = img.crop((left, top, right, bottom)).resize((w, h), Image.Resampling.BILINEAR)

    # 2. Exposure / Brightness shift (+- 15%)
    brightness_factor = rng.uniform(0.85, 1.15)
    enhanced = ImageEnhance.Brightness(cropped).enhance(brightness_factor)

    # 3. Slight angle rotation (-4 to +4 degrees)
    rot_angle = rng.uniform(-4.0, 4.0)
    rotated = enhanced.rotate(rot_angle, resample=Image.Resampling.BILINEAR)

    return rotated


def bootstrap_classification_metrics(
    y_true: List[int],
    y_pred: List[int],
    n_iterations: int = 1000,
    seed: int = 42
) -> Dict[str, Any]:
    """Computes Precision, Recall, and F1 with 95% bootstrap confidence intervals."""
    from sklearn.metrics import precision_score, recall_score, f1_score

    p = precision_score(y_true, y_pred, zero_division=0)
    r = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    rng = np.random.RandomState(seed)
    n = len(y_true)
    f1_boots, p_boots, r_boots = [], [], []

    for _ in range(n_iterations):
        idx = rng.choice(n, size=n, replace=True)
        t_sub = [y_true[i] for i in idx]
        p_sub = [y_pred[i] for i in idx]
        f1_boots.append(f1_score(t_sub, p_sub, zero_division=0))
        p_boots.append(precision_score(t_sub, p_sub, zero_division=0))
        r_boots.append(recall_score(t_sub, p_sub, zero_division=0))

    return {
        "precision": round(float(p), 3),
        "precision_95ci": [round(float(np.percentile(p_boots, 2.5)), 3), round(float(np.percentile(p_boots, 97.5)), 3)],
        "recall": round(float(r), 3),
        "recall_95ci": [round(float(np.percentile(r_boots, 2.5)), 3), round(float(np.percentile(r_boots, 97.5)), 3)],
        "f1_score": round(float(f1), 3),
        "f1_95ci": [round(float(np.percentile(f1_boots, 2.5)), 3), round(float(np.percentile(f1_boots, 97.5)), 3)]
    }


def run_duplicate_evaluation(
    images_dir: str = "data/ood_bengaluru/images",
    pairs_per_image: int = 2,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Evaluates visual and multimodal duplicate detection over positive and negative pairs.
    """
    random.seed(seed)
    np.random.seed(seed)

    print("\n" + "=" * 80)
    print("      CIVICPULSE AI — DUPLICATE DETECTION BENCHMARK (v2)")
    print("      (Bitwise pHash vs. OpenCLIP Embeddings on Augmentation Pairs)")
    print("=" * 80)
    print("Disclaimer: Optimistic synthetic evaluation using data augmentations on fixture images.")
    print("Does not substitute for a real-world field-validated duplicate pair benchmark.\n")

    img_files = sorted(list(Path(images_dir).glob("*.jpg")))
    if not img_files:
        raise FileNotFoundError(f"No benchmark images found in {images_dir}")

    heuristic = HeuristicAnalyzer()
    zeroshot = ZeroShotAnalyzer()

    # Create temporary augmented images for positive pairs
    aug_dir = Path("data/ood_bengaluru/augmented_pairs")
    aug_dir.mkdir(parents=True, exist_ok=True)

    pairs = []  # (path_a, path_b, is_duplicate: int)

    # 1. Generate Positive Pairs (same scene, transformed)
    for idx, orig_path in enumerate(img_files):
        with Image.open(orig_path) as img:
            for p_idx in range(pairs_per_image):
                aug_img = apply_citizen_photo_augmentations(img, seed=seed + idx * 10 + p_idx)
                aug_filename = aug_dir / f"AUG_{orig_path.stem}_{p_idx}.jpg"
                aug_img.save(aug_filename, "JPEG")
                pairs.append((str(orig_path), str(aug_filename), 1))

    # 2. Generate Negative Pairs (different physical scenes)
    n_pos = len(pairs)
    for _ in range(n_pos):
        a, b = random.sample(img_files, 2)
        pairs.append((str(a), str(b), 0))

    random.shuffle(pairs)
    print(f"Total Evaluated Image Pairs: N = {len(pairs)} ({n_pos} positive duplicates, {n_pos} negative non-duplicates)\n")

    # Evaluate Method A: Bitwise pHash
    # Evaluate Method B: OpenCLIP ViT-B/32
    y_true = [p[2] for p in pairs]
    y_pred_phash = []
    y_pred_clip = []

    phash_threshold = 0.75
    clip_threshold = 0.82

    t0_phash = time.perf_counter()
    for path_a, path_b, _ in pairs:
        hash_a = heuristic.compute_perceptual_hash(Image.open(path_a))
        hash_b = heuristic.compute_perceptual_hash(Image.open(path_b))
        sim = DuplicateService.bitwise_hash_similarity(hash_a, hash_b)
        y_pred_phash.append(1 if (sim is not None and sim >= phash_threshold) else 0)
    time_phash = (time.perf_counter() - t0_phash) * 1000.0 / len(pairs)

    t0_clip = time.perf_counter()
    for path_a, path_b, _ in pairs:
        emb_a = zeroshot.extract_image_embedding(path_a)
        emb_b = zeroshot.extract_image_embedding(path_b)
        sim = EmbeddingService.cosine_similarity(emb_a, emb_b)
        y_pred_clip.append(1 if (sim is not None and sim >= clip_threshold) else 0)
    time_clip = (time.perf_counter() - t0_clip) * 1000.0 / len(pairs)

    metrics_phash = bootstrap_classification_metrics(y_true, y_pred_phash, seed=seed)
    metrics_clip = bootstrap_classification_metrics(y_true, y_pred_clip, seed=seed)

    print("--- Evaluation Results (95% Bootstrap CI) ---")
    print(f"[Method A: Bitwise pHash (tau >= {phash_threshold:.2f})]")
    print(f"  Precision: {metrics_phash['precision']:.1%} (95% CI: [{metrics_phash['precision_95ci'][0]:.1%}, {metrics_phash['precision_95ci'][1]:.1%}])")
    print(f"  Recall:    {metrics_phash['recall']:.1%} (95% CI: [{metrics_phash['recall_95ci'][0]:.1%}, {metrics_phash['recall_95ci'][1]:.1%}])")
    print(f"  F1-Score:  {metrics_phash['f1_score']:.3f} (95% CI: [{metrics_phash['f1_95ci'][0]:.3f}, {metrics_phash['f1_95ci'][1]:.3f}])")
    print(f"  Mean Pair Comparison Time: {time_phash:.2f} ms\n")

    print(f"[Method B: OpenCLIP ViT-B/32 Embeddings (tau >= {clip_threshold:.2f})]")
    print(f"  Precision: {metrics_clip['precision']:.1%} (95% CI: [{metrics_clip['precision_95ci'][0]:.1%}, {metrics_clip['precision_95ci'][1]:.1%}])")
    print(f"  Recall:    {metrics_clip['recall']:.1%} (95% CI: [{metrics_clip['recall_95ci'][0]:.1%}, {metrics_clip['recall_95ci'][1]:.1%}])")
    print(f"  F1-Score:  {metrics_clip['f1_score']:.3f} (95% CI: [{metrics_clip['f1_95ci'][0]:.3f}, {metrics_clip['f1_95ci'][1]:.3f}])")
    print(f"  Mean Pair Comparison Time: {time_clip:.2f} ms\n")

    results = {
        "benchmark_description": "Optimistic synthetic evaluation of duplicate visual detection on augmentation pairs.",
        "disclaimer": "Smoke test only on synthetic augmentation pairs; not evidence of real-world duplicate performance.",
        "total_pairs": len(pairs),
        "positive_pairs": n_pos,
        "negative_pairs": n_pos,
        "method_phash_bitwise": {
            "threshold": phash_threshold,
            "metrics": metrics_phash,
            "mean_latency_ms": round(time_phash, 2)
        },
        "method_openclip_embeddings": {
            "threshold": clip_threshold,
            "metrics": metrics_clip,
            "mean_latency_ms": round(time_clip, 2)
        }
    }

    out_file = Path("ml/eval/duplicate_benchmark_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Detailed duplicate benchmark saved to: {out_file}\n")
    return results


if __name__ == "__main__":
    run_duplicate_evaluation()
