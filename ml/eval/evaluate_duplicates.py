"""
Duplicate Detection Benchmark: Bitwise pHash vs. OpenCLIP Image Embeddings
==========================================================================
Evaluates visual similarity techniques on synthetic fixtures and augmentation pairs:
1. Method A: Perceptual Hash (64-bit dHash / pHash with bitwise Hamming distance).
2. Method B: OpenCLIP ViT-B/32 Cosine Similarity.

METHODOLOGY & HARDENING:
------------------------
- Positives: Synthetic augmentation-derived pairs (crop, perspective, rotation, exposure).
- Negatives:
  * Easy Negatives: Different categories, different physical scenes.
  * Hard Negatives: Same category, simulated within 200m spatial proximity, different physical defect images.
- Rigorous Validation/Test Split (50% validation, 50% held-out test).
- Threshold Selection: Optimal F1 threshold is selected exclusively on the validation set.
- Test Reporting: Precision, Recall, F1, and 95% bootstrap confidence intervals are computed on the held-out test set.
- Label: 'synthetic fixtures, augmentation positives'.
"""

import os
import sys
import time
import json
import random
import csv
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from PIL import Image, ImageEnhance

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


def find_optimal_threshold(
    y_true: List[int],
    scores: List[float],
    threshold_range: Tuple[float, float, float] = (0.40, 0.95, 0.01)
) -> Tuple[float, float]:
    """Sweeps thresholds on validation set to find the threshold that maximizes F1 score."""
    from sklearn.metrics import f1_score

    best_thresh = threshold_range[0]
    best_f1 = -1.0

    start, stop, step = threshold_range
    current = start
    while current <= stop:
        preds = [1 if (s is not None and s >= current) else 0 for s in scores]
        f1 = f1_score(y_true, preds, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = round(current, 3)
        current += step

    return best_thresh, round(float(best_f1), 3)


def load_ood_metadata(labels_csv: Path) -> Dict[str, Dict[str, Any]]:
    """Loads image category and location metadata from labels.csv."""
    meta = {}
    if labels_csv.exists():
        with open(labels_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                meta[row["image_id"]] = {
                    "category": row["ground_truth_category"],
                    "location": row["location"]
                }
    return meta


def run_duplicate_evaluation(
    images_dir: str = "data/ood_bengaluru/images",
    labels_csv: str = "data/ood_bengaluru/labels.csv",
    pairs_per_image: int = 2,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Evaluates visual and multimodal duplicate detection with hard negatives,
    a 50/50 validation/test split, and validation-only threshold tuning.
    """
    random.seed(seed)
    np.random.seed(seed)

    print("\n" + "=" * 80)
    print("      CIVICPULSE AI — HARDENED DUPLICATE DETECTION BENCHMARK")
    print("      (Hard Negatives, Validation/Test Split & Bootstrap CIs)")
    print("=" * 80)
    print("Dataset Label: synthetic fixtures, augmentation positives")
    print("Disclaimer: Smoke test on synthetic fixtures; not evidence of real-world duplicate performance.\n")

    img_files = sorted(list(Path(images_dir).glob("*.jpg")))
    if not img_files:
        raise FileNotFoundError(f"No benchmark images found in {images_dir}")

    metadata = load_ood_metadata(Path(labels_csv))

    heuristic = HeuristicAnalyzer()
    zeroshot = ZeroShotAnalyzer()

    # Precompute perceptual hashes and CLIP embeddings for unique base images
    cache_phash: Dict[str, str] = {}
    cache_clip: Dict[str, Optional[List[float]]] = {}

    print("Pre-computing feature embeddings for base fixtures...")
    for p in img_files:
        sp = str(p)
        with Image.open(sp) as im:
            cache_phash[sp] = heuristic.compute_perceptual_hash(im)
        cache_clip[sp] = zeroshot.extract_image_embedding(sp)

    # Create temporary augmented images for positive pairs
    aug_dir = Path("data/ood_bengaluru/augmented_pairs")
    aug_dir.mkdir(parents=True, exist_ok=True)

    # Group base images by category for hard negative generation
    cat_to_images: Dict[str, List[str]] = {}
    for p in img_files:
        stem = p.stem
        cat = metadata.get(stem, {}).get("category", "unknown")
        cat_to_images.setdefault(cat, []).append(str(p))

    # Construct Pairs: (path_a, path_b, is_duplicate: int, pair_type: str)
    pairs: List[Tuple[str, str, int, str]] = []

    # 1. POSITIVE PAIRS: Same physical defect, augmented citizen camera view
    print("Generating positive augmentation pairs...")
    for idx, orig_path in enumerate(img_files):
        with Image.open(orig_path) as img:
            for p_idx in range(pairs_per_image):
                aug_img = apply_citizen_photo_augmentations(img, seed=seed + idx * 10 + p_idx)
                aug_filename = aug_dir / f"AUG_{orig_path.stem}_{p_idx}.jpg"
                aug_img.save(aug_filename, "JPEG")
                sp_aug = str(aug_filename)
                with Image.open(sp_aug) as a_im:
                    cache_phash[sp_aug] = heuristic.compute_perceptual_hash(a_im)
                cache_clip[sp_aug] = zeroshot.extract_image_embedding(sp_aug)

                pairs.append((str(orig_path), sp_aug, 1, "positive_augmentation"))

    n_pos = len(pairs)

    # 2. EASY NEGATIVE PAIRS: Different category, different physical defect
    print("Generating easy negative pairs (different categories)...")
    all_categories = list(cat_to_images.keys())
    easy_negs: List[Tuple[str, str, int, str]] = []
    attempts = 0
    while len(easy_negs) < (n_pos // 2) and attempts < 1000:
        attempts += 1
        cat_a, cat_b = random.sample(all_categories, 2)
        if cat_a != cat_b and cat_to_images[cat_a] and cat_to_images[cat_b]:
            img_a = random.choice(cat_to_images[cat_a])
            img_b = random.choice(cat_to_images[cat_b])
            easy_negs.append((img_a, img_b, 0, "easy_negative"))
    pairs.extend(easy_negs)

    # 3. HARD NEGATIVE PAIRS: Same category, within simulated 200m, DIFFERENT defect image
    print("Generating hard negative pairs (same category, different defect image)...")
    hard_negs: List[Tuple[str, str, int, str]] = []
    # Identify categories with at least 2 distinct images
    multi_img_cats = [c for c, imgs in cat_to_images.items() if len(imgs) >= 2]
    attempts = 0
    while len(hard_negs) < (n_pos // 2) and attempts < 1000:
        attempts += 1
        cat = random.choice(multi_img_cats)
        img_a, img_b = random.sample(cat_to_images[cat], 2)
        hard_negs.append((img_a, img_b, 0, "hard_negative"))
    pairs.extend(hard_negs)

    print(f"Total Constructed Pairs: N = {len(pairs)}")
    print(f"  * Positives (Augmentation): {n_pos}")
    print(f"  * Easy Negatives (Diff Category): {len(easy_negs)}")
    print(f"  * Hard Negatives (Same Category, Diff Image): {len(hard_negs)}\n")

    # 4. STRATIFIED VALIDATION / TEST SPLIT (50% / 50%)
    from sklearn.model_selection import train_test_split

    pair_types = [p[3] for p in pairs]
    val_pairs, test_pairs = train_test_split(
        pairs,
        test_size=0.5,
        random_state=seed,
        stratify=pair_types
    )

    print(f"Dataset Split: Validation N={len(val_pairs)} | Held-Out Test N={len(test_pairs)}\n")

    # Compute similarity scores for validation and test sets
    def score_pairs(pair_list: List[Tuple[str, str, int, str]]) -> Tuple[List[int], List[float], List[float]]:
        y_true, phash_scores, clip_scores = [], [], []
        for path_a, path_b, label, _ in pair_list:
            y_true.append(label)
            # pHash similarity
            sim_ph = DuplicateService.bitwise_hash_similarity(cache_phash[path_a], cache_phash[path_b])
            phash_scores.append(sim_ph if sim_ph is not None else 0.0)
            # CLIP similarity
            sim_cl = EmbeddingService.cosine_similarity(cache_clip[path_a], cache_clip[path_b])
            clip_scores.append(sim_cl if sim_cl is not None else 0.0)
        return y_true, phash_scores, clip_scores

    val_y, val_phash_scores, val_clip_scores = score_pairs(val_pairs)
    test_y, test_phash_scores, test_clip_scores = score_pairs(test_pairs)

    # 5. THRESHOLD TUNING (ON VALIDATION SET ONLY)
    print("--- Tuning Thresholds on Validation Set ---")
    opt_thresh_phash, val_f1_phash = find_optimal_threshold(val_y, val_phash_scores, (0.40, 0.95, 0.01))
    opt_thresh_clip, val_f1_clip = find_optimal_threshold(val_y, val_clip_scores, (0.50, 0.95, 0.01))
    print(f"Optimal pHash Validation Threshold: tau = {opt_thresh_phash:.2f} (Val F1: {val_f1_phash:.3f})")
    print(f"Optimal OpenCLIP Validation Threshold: tau = {opt_thresh_clip:.2f} (Val F1: {val_f1_clip:.3f})\n")

    # 6. EVALUATION ON HELD-OUT TEST SET (USING VALIDATION THRESHOLDS)
    test_preds_phash = [1 if s >= opt_thresh_phash else 0 for s in test_phash_scores]
    test_preds_clip = [1 if s >= opt_thresh_clip else 0 for s in test_clip_scores]

    test_metrics_phash = bootstrap_classification_metrics(test_y, test_preds_phash, seed=seed)
    test_metrics_clip = bootstrap_classification_metrics(test_y, test_preds_clip, seed=seed)

    print("=" * 80)
    print("--- HELD-OUT TEST EVALUATION RESULTS (95% Bootstrap CI) ---")
    print("=" * 80)
    print(f"[Method A: Bitwise pHash (tau = {opt_thresh_phash:.2f} chosen on val)]")
    print(f"  Test Precision: {test_metrics_phash['precision']:.1%} (95% CI: [{test_metrics_phash['precision_95ci'][0]:.1%}, {test_metrics_phash['precision_95ci'][1]:.1%}])")
    print(f"  Test Recall:    {test_metrics_phash['recall']:.1%} (95% CI: [{test_metrics_phash['recall_95ci'][0]:.1%}, {test_metrics_phash['recall_95ci'][1]:.1%}])")
    print(f"  Test F1-Score:  {test_metrics_phash['f1_score']:.3f} (95% CI: [{test_metrics_phash['f1_95ci'][0]:.3f}, {test_metrics_phash['f1_95ci'][1]:.3f}])\n")

    print(f"[Method B: OpenCLIP ViT-B/32 Cosine (tau = {opt_thresh_clip:.2f} chosen on val)]")
    print(f"  Test Precision: {test_metrics_clip['precision']:.1%} (95% CI: [{test_metrics_clip['precision_95ci'][0]:.1%}, {test_metrics_clip['precision_95ci'][1]:.1%}])")
    print(f"  Test Recall:    {test_metrics_clip['recall']:.1%} (95% CI: [{test_metrics_clip['recall_95ci'][0]:.1%}, {test_metrics_clip['recall_95ci'][1]:.1%}])")
    print(f"  Test F1-Score:  {test_metrics_clip['f1_score']:.3f} (95% CI: [{test_metrics_clip['f1_95ci'][0]:.3f}, {test_metrics_clip['f1_95ci'][1]:.3f}])\n")

    results = {
        "benchmark_label": "synthetic fixtures, augmentation positives",
        "methodology": "50/50 validation/test split; thresholds selected on validation only; evaluated on held-out test with hard negatives.",
        "disclaimer": "Smoke test on synthetic fixtures; not evidence of real-world duplicate performance.",
        "total_pairs": len(pairs),
        "validation_pairs": len(val_pairs),
        "test_pairs": len(test_pairs),
        "pair_breakdown": {
            "positive_augmentations": n_pos,
            "easy_negatives": len(easy_negs),
            "hard_negatives": len(hard_negs)
        },
        "validation_tuning": {
            "phash_threshold": opt_thresh_phash,
            "phash_val_f1": val_f1_phash,
            "clip_threshold": opt_thresh_clip,
            "clip_val_f1": val_f1_clip
        },
        "held_out_test_metrics": {
            "method_phash_bitwise": {
                "threshold": opt_thresh_phash,
                "metrics": test_metrics_phash
            },
            "method_openclip_embeddings": {
                "threshold": opt_thresh_clip,
                "metrics": test_metrics_clip
            }
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
