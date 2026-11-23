# CivicPulse AI — Real Photo Collection & Annotation Guide

This guide provides standard operating procedures (SOP) for collecting and annotating authentic civic infrastructure defect photographs in Bengaluru for out-of-distribution (OOD) testing and visual duplicate detection evaluation.

---

## 1. Safety & Ethical Field Protocols (CRITICAL)

### A. Physical Safety Near Traffic
1. **Never step into active vehicular traffic**: Capture images from footpaths, pedestrian walkways, sidewalk curbs, or safe road shoulders.
2. **Wear bright clothing**: When collecting photos near busy arterial roads (e.g., Outer Ring Road, Hosur Road, 80 Feet Road), remain alert to two-wheelers mounting sidewalks.
3. **Do not shoot while riding or driving**: Stop and stabilize your position before photographing any defect.

### B. Citizen Privacy Protection
Civic infrastructure evaluation evaluates physical defects, not people. To ensure compliance with privacy regulations:
1. **No Pedestrian Faces**: Ensure no identifiable faces of pedestrians, street vendors, or bystanders appear in the frame. If unavoidable, stand at an angle where the face is not visible, or wait until the sidewalk clears.
2. **No Vehicle Number Plates**: Frame your photograph to exclude vehicle registration plates, or frame closely around the asphalt crater/defect.
3. **No Private Residential Properties**: Frame strictly toward public civic infrastructure (roads, sidewalks, streetlights, stormwater drains, public bins). Do not photograph private home interiors, gates, or courtyards.

---

## 2. Category Photography Guidelines

Capture a target of at least **12 images per category** across the 8 civic defect categories:

| Category Code | Subject Matter | Distance | Recommended Camera Angle |
| :--- | :--- | :--- | :--- |
| `pothole` | Depressions, asphalt craters, surface voids | 1.5 m – 3.0 m | 45° to 60° downward pitch showing depth and crater edge |
| `road_damage` | Longitudinal, transverse, alligator cracks, rutting | 2.0 m – 4.0 m | 45° angle showing crack pattern and road surface context |
| `garbage_overflow` | Full municipal bins with spillage, uncollected bags | 3.0 m – 6.0 m | Eye-level or slight downward pitch showing bin and perimeter |
| `illegal_dumping` | Construction debris, uncontained roadside dumps | 4.0 m – 8.0 m | Wide framing capturing the scale of the dump pile |
| `water_leakage` | Pipe bursts, bubbling pavement water, valve leaks | 2.0 m – 4.0 m | 45° angle highlighting pooled water and surface origin |
| `blocked_drain` | Silted stormwater drains, debris blocking grates | 1.5 m – 3.0 m | 60° steep angle into the drain channel or grate surface |
| `broken_streetlight` | Damaged luminaires, open wiring, unlit fixtures | 5.0 m – 10.0 m | Upward low-angle shot showing the pole and head fixture |
| `damaged_infrastructure` | Broken footpath slabs, missing railings, manholes | 1.5 m – 3.5 m | 45° angle showing tripping hazard and displacement |

---

## 3. Duplicate Pair Collection Protocol

To evaluate visual duplicate detection (pHash vs. OpenCLIP embeddings), capture **Same-Defect Pairs** and **Hard Negatives**:

### A. Same-Defect Pairs (Positives: `is_same_defect = 1`)
- Take Photo A of a defect from your initial vantage point (e.g., looking North).
- Walk 3 to 5 meters to the side or change your elevation (e.g., looking East at a 45° offset).
- Take Photo B of the **exact same physical defect**.
- This introduces realistic viewpoint, perspective, and lighting shifts without synthetic augmentation artifacts.

### B. Hard Negative Pairs (Negatives: `is_same_defect = 0`)
- Find two **different** defects of the **same category** located within the same road segment or neighborhood (within ~50–200 m).
  - *Example*: Pothole #1 near Junction A, and Pothole #2 60 meters down the street.
- Pair them in `pairs.csv` with `is_same_defect = 0`.
- This tests whether visual duplicate detection can distinguish two different potholes rather than collapsing solely because both are potholes.

---

## 4. Annotation Format

### A. Single Image Ground Truth: `labels.csv`
Place images in `data/ood_bengaluru_real/images/` and record each row in `data/ood_bengaluru_real/labels.csv`:
```csv
image_filename,category,notes,timestamp,latitude,longitude
pothole_blr_01.jpg,pothole,"Deep crater on 80ft road near edge",2026-11-23T10:15:00Z,12.9352,77.6245
pothole_blr_02.jpg,pothole,"Same pothole from 45 deg east perspective",2026-11-23T10:16:00Z,12.9352,77.6245
garbage_blr_01.jpg,garbage_overflow,"Overflowing municipal bin at corner",2026-11-23T10:45:00Z,12.9784,77.6408
```

### B. Pair Annotations: `pairs.csv`
Record pairs in `data/ood_bengaluru_real/pairs.csv`:
```csv
image_a,image_b,is_same_defect,category,distance_meters,notes
pothole_blr_01.jpg,pothole_blr_02.jpg,1,pothole,3.5,"Same pothole photographed from north and east angles"
pothole_blr_01.jpg,pothole_blr_03.jpg,0,pothole,75.0,"Hard negative: different pothole 75m down the same street"
```

---

## 5. Validation and Execution

Once you have added photos and updated the CSV files:
1. **Validate Dataset Quality**:
   ```bash
   python scripts/validate_photo_folder.py --data-dir data/ood_bengaluru_real --min-per-category 12
   ```
2. **Run OOD Classification Benchmark on Real Photos**:
   ```bash
   python ml/eval/evaluate_ood.py --dataset real
   ```
3. **Run Duplicate Detection Benchmark on Real Pairs**:
   ```bash
   python ml/eval/evaluate_duplicates.py --dataset real
   ```
Results will be saved to `ml/eval/ood_benchmark_results_real.json` and `ml/eval/duplicate_benchmark_results_real.json` respectively, and automatically labelled as *"real phone photos, N=..., single annotator"*.
