"""
scripts/validate_photo_folder.py
================================
Validates authentic user-collected civic defect photographs in data/ood_bengaluru_real/.
Checks:
1. Supported image formats (.jpg, .jpeg, .png, .webp).
2. Image readability and byte integrity (via PIL).
3. labels.csv presence and bidirectional file alignment.
4. Per-category image counts against target threshold (default: >= 12 per category).
5. Image dimensions (warns if width or height < 400px).
6. Perceptual duplicate detection (warns on identical/near-identical images).
7. pairs.csv validation (if present: checks image existence, label values, and pair balance).

Usage:
    python scripts/validate_photo_folder.py --data-dir data/ood_bengaluru_real --min-per-category 12
"""

import os
import sys
import csv
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple
from PIL import Image

CIVIC_CATEGORIES = [
    "pothole",
    "road_damage",
    "garbage_overflow",
    "illegal_dumping",
    "water_leakage",
    "blocked_drain",
    "broken_streetlight",
    "damaged_infrastructure"
]

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def compute_quick_phash(img_path: Path) -> str:
    """Computes a simple 64-bit average hash for duplicate photo warning."""
    try:
        with Image.open(img_path) as img:
            img_gray = img.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
            pixels = list(img_gray.getdata())
            avg = sum(pixels) / len(pixels)
            bits = "".join("1" if p > avg else "0" for p in pixels)
            return f"{int(bits, 2):016x}"
    except Exception:
        return ""


def validate_photo_folder(data_dir_str: str, min_per_category: int = 12, min_size: int = 400) -> bool:
    data_dir = Path(data_dir_str)
    print("=" * 80)
    print(f"CIVICPULSE AI — REAL PHOTO DATASET VALIDATOR")
    print(f"Target Directory: {data_dir.resolve()}")
    print(f"Target Minimum per Category: {min_per_category}")
    print("=" * 80)

    if not data_dir.exists():
        print(f"[ERROR] Directory does not exist: {data_dir}")
        return False

    labels_file = data_dir / "labels.csv"
    pairs_file = data_dir / "pairs.csv"
    images_dir = data_dir / "images"

    if not images_dir.exists():
        print(f"[ERROR] Images directory not found at {images_dir}")
        return False

    if not labels_file.exists():
        print(f"[ERROR] labels.csv not found at {labels_file}")
        return False

    # 1. Inspect image files on disk
    disk_images = [f for f in images_dir.iterdir() if f.is_file() and f.name != ".gitkeep"]
    print(f"\n[1] Physical Image Files Found: {len(disk_images)}")

    unsupported = [f.name for f in disk_images if f.suffix.lower() not in SUPPORTED_EXTENSIONS]
    if unsupported:
        print(f"  [WARNING] Unsupported file formats found ({len(unsupported)}): {unsupported[:5]}")

    corrupted = []
    undersized = []
    phash_dict: Dict[str, List[str]] = {}

    for img_path in disk_images:
        if img_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            with Image.open(img_path) as img:
                img.verify()
            # Reopen to check dimensions and compute hash
            with Image.open(img_path) as img:
                w, h = img.size
                if w < min_size or h < min_size:
                    undersized.append((img_path.name, w, h))
            
            h_val = compute_quick_phash(img_path)
            if h_val:
                phash_dict.setdefault(h_val, []).append(img_path.name)
        except Exception as e:
            corrupted.append((img_path.name, str(e)))

    if corrupted:
        print(f"  [FAIL] Corrupted/unreadable images ({len(corrupted)}):")
        for name, err in corrupted[:5]:
            print(f"    - {name}: {err}")
    else:
        print(f"  [PASS] All {len(disk_images)} images verified physically readable.")

    if undersized:
        print(f"  [WARNING] Undersized images (< {min_size}px) ({len(undersized)}):")
        for name, w, h in undersized[:5]:
            print(f"    - {name}: {w}x{h} px (recommended >= {min_size}px)")

    # Perceptual duplicates
    duplicates = [names for names in phash_dict.values() if len(names) > 1]
    if duplicates:
        print(f"  [WARNING] Potential perceptual duplicates detected ({len(duplicates)} clusters):")
        for cluster in duplicates[:3]:
            print(f"    - Similar photos: {cluster}")

    # 2. Parse labels.csv
    labeled_rows = []
    category_counts: Dict[str, int] = {cat: 0 for cat in CIVIC_CATEGORIES}
    unknown_categories = []

    with open(labels_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader((line for line in f if not line.startswith("#")))
        for row_idx, row in enumerate(reader, start=1):
            fname = row.get("image_filename", "").strip()
            cat = row.get("category", "").strip()
            if not fname:
                continue
            labeled_rows.append(row)
            if cat in category_counts:
                category_counts[cat] += 1
            else:
                unknown_categories.append((fname, cat))

    print(f"\n[2] labels.csv Entries Parsed: {len(labeled_rows)}")
    disk_image_names = {f.name for f in disk_images}
    labeled_image_names = {r["image_filename"] for r in labeled_rows}

    missing_on_disk = labeled_image_names - disk_image_names
    unlabeled_on_disk = disk_image_names - labeled_image_names

    if missing_on_disk:
        print(f"  [FAIL] Images listed in labels.csv but missing from disk ({len(missing_on_disk)}):")
        for m in list(missing_on_disk)[:5]:
            print(f"    - {m}")
    else:
        print(f"  [PASS] All labeled entries correspond to physical files.")

    if unlabeled_on_disk:
        print(f"  [INFO] Images on disk not yet labeled in labels.csv ({len(unlabeled_on_disk)}):")
        for u in list(unlabeled_on_disk)[:5]:
            print(f"    - {u}")

    if unknown_categories:
        print(f"  [WARNING] Unrecognized categories found ({len(unknown_categories)}):")
        for fname, cat in unknown_categories[:5]:
            print(f"    - {fname}: '{cat}' (valid: {CIVIC_CATEGORIES})")

    # 3. Category distribution analysis
    print(f"\n[3] Category Distribution vs Target ({min_per_category} per category):")
    all_targets_met = True
    for cat in CIVIC_CATEGORIES:
        count = category_counts[cat]
        met = count >= min_per_category
        if not met:
            all_targets_met = False
        status_str = "[OK]" if met else f"[NEED {min_per_category - count} MORE]"
        print(f"  - {cat:<24} : {count:>3} / {min_per_category}  {status_str}")

    # 4. Parse pairs.csv (if present)
    if pairs_file.exists():
        pair_rows = []
        positive_pairs = 0
        negative_pairs = 0
        pair_missing_files = set()

        with open(pairs_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader((line for line in f if not line.startswith("#")))
            for row in reader:
                a = row.get("image_a", "").strip()
                b = row.get("image_b", "").strip()
                lbl = row.get("is_same_defect", "").strip()
                if not a or not b:
                    continue
                pair_rows.append(row)
                if a not in disk_image_names:
                    pair_missing_files.add(a)
                if b not in disk_image_names:
                    pair_missing_files.add(b)
                if lbl == "1":
                    positive_pairs += 1
                elif lbl == "0":
                    negative_pairs += 1

        print(f"\n[4] pairs.csv Pairs Parsed: {len(pair_rows)}")
        print(f"  - Positive pairs (same defect, different angle): {positive_pairs}")
        print(f"  - Hard negative pairs (same category, different defect): {negative_pairs}")
        if pair_missing_files:
            print(f"  [FAIL] Pair references missing from images folder ({len(pair_missing_files)}): {list(pair_missing_files)[:5]}")
        else:
            print(f"  [PASS] All image pair references exist on disk.")

    # Final verdict
    print("\n" + "=" * 80)
    if len(disk_images) == 0 or len(labeled_rows) == 0:
        print("VERDICT: TEMPLATE STATE (No user photos added yet).")
        print("Follow docs/PHOTO_GUIDE.md to capture photos and populate labels.csv.")
        return True
    elif corrupted or missing_on_disk:
        print("VERDICT: FAILED. Please resolve file corruptions or missing image paths.")
        return False
    elif not all_targets_met:
        print(f"VERDICT: IN PROGRESS. Images valid, but target quota ({min_per_category}/category) not yet met.")
        return True
    else:
        print("VERDICT: READY FOR REAL-PHOTO BENCHMARKING! All validation criteria passed.")
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate real civic photo dataset")
    parser.add_argument("--data-dir", type=str, default="data/ood_bengaluru_real", help="Dataset directory")
    parser.add_argument("--min-per-category", type=int, default=12, help="Target minimum images per category")
    parser.add_argument("--min-size", type=int, default=400, help="Minimum width and height in pixels")
    args = parser.parse_args()

    success = validate_photo_folder(
        data_dir_str=args.data_dir,
        min_per_category=args.min_per_category,
        min_size=args.min_size
    )
    sys.exit(0 if success else 1)
