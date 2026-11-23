# Model Card — CivicPulse AI Vision & Prioritization Suite

## 1. Model Details

- **Model Suite Name**: CivicPulse AI Multi-Model Decision Support Suite
- **Version**: 2.1.0
- **Architectural Approach**: Multi-Model Pipeline combining rule-based heuristics, deep learning zero-shot classification, road defect object detection, geospatial network analysis, and multi-factor ranking.
- **Components**:
  1. `HeuristicAnalyzer`: Deterministic classical computer vision (Sobel edge density, HSV dark-pixel shadow ratio, saturation variance, 64-bit dHash/pHash perceptual hashing).
  2. `ZeroShotAnalyzer`: OpenCLIP ViT-B/32 foundation model utilizing calibrated text prompt ensembles across broader civic issue categories.
  3. `DuplicateService` (v2): Multimodal duplicate detection combining two-tier spatial gating (50m pre-filter + category thresholds), OpenCLIP ViT-B/32 cosine similarity, bitwise pHash, and exponential time decay.
  4. `PriorityService` (v2): Explainable 5-factor municipal prioritization engine featuring OpenStreetMap POI risk scoring and continuous saturating age escalation.
  5. `PrivacyService`: Best-effort OpenCV Haar Cascade PII face blurring using bundled model (plate redaction not implemented).
  6. `ResolutionVerificationService`: Before/after contractor repair verification via GPS proximity, OpenCLIP scene consistency, and texture change analysis.

---

## 2. Intended Use & Target Tasks

- **Primary Task**: Assist municipal triage officers in categorizing civic infrastructure grievances, filtering duplicate complaint bursts, prioritizing high-risk hazards, and verifying repair completion.
- **Target Geography**: Bengaluru Metropolitan Region (Bruhat Bengaluru Mahanagara Palike - BBMP jurisdiction).
- **Out-of-Scope Uses**: Autonomous decision-making, automated legal or punitive actions, direct contractor payments without human sign-off, or millimeter-precise physical structural depth measurements.

---

## 3. Computer Vision Triage Architecture

### 3.1 Multi-Model Pipeline & The BaseAnalyzer Contract
All vision analyzers adhere to the `BaseAnalyzer` contract (`backend/app/ml/base.py`):
- Analyzers return an `AnalyzerResult` containing:
  - `predicted_category`: Mapped canonical category code.
  - `confidence`: Calibrated confidence in $[0.0, 1.0]$.
  - `status`: One of `{"success", "abstain", "fallback"}`.
  - `detected_features`: Extracted numeric features for auditability.
  - `bounding_boxes`: Pixel-space detections with relative coverage area.

### 3.2 RoadDefectDetector & Honest Abstention Policy
- Designed to run YOLOv8n object detection exported to ONNX Runtime.
- **Abstention Contract**: When pre-trained weights (`models/rdd2022_yolov8n.onnx`) are absent, the detector emits `status="abstain"` rather than fabricating detections or guessing.
- Triage gracefully falls back to the `ZeroShotAnalyzer` and `HeuristicAnalyzer`.

### 3.3 ZeroShotAnalyzer (OpenCLIP ViT-B/32)
- Evaluates similarity against tailored prompt ensembles for non-road civic issues:
  - *Garbage Overflow*: "a photograph of an overflowing municipal waste bin with trash spilling onto the street"
  - *Illegal Dumping*: "a photograph of construction demolition debris, industrial waste, and rubble dumped outdoors"
  - *Water Leakage*: "a photograph of a ruptured water supply pipeline gushing potable water onto the road"
  - *Blocked Drain*: "a photograph of a clogged stormwater drain or roadside gutter overflowing with black sewage"
  - *Broken Streetlight*: "a photograph of a broken street luminaire fixture, damaged lighting pole, or unlit streetlight"
  - *Damaged Infrastructure*: "a photograph of broken pedestrian sidewalk slabs, collapsed railing, or damaged public shelter"
- **Calibrated Abstention**: If the softmax confidence over civic prompts is $< 0.35$, the analyzer emits `status="abstain"`.

---

## 4. Priority Scoring Engine v2

### 4.1 Scoring Formula
$$\text{Priority} = 0.35 \times S_{\text{sev}} + 0.25 \times S_{\text{safe}} + 0.15 \times S_{\text{loc}} + 0.15 \times S_{\text{comm}} + 0.10 \times S_{\text{age}}$$

- **Factor 1: Physical Severity (35%)**: Scaled 1–10 from visual defect bounding box area, dark shadow variance, and keyword intensity.
- **Factor 2: Category Hazard Weight (25%)**: Inherent public safety risk (Water Leakage / Blocked Drain = 0.85, Pothole = 0.75, Streetlight = 0.65).
- **Factor 3: Location Risk (15%)**: Geodesic proximity to 30 high-priority facilities (+35% for hospitals $\le 100\text{m}$, +30% for schools/transit $\le 100\text{m}$) using OpenStreetMap data.
- **Factor 4: Community Impact (15%)**: Citizen report frequency and upvotes ($15 \times \log_2(1 + N_{\text{upvotes}})$).
- **Factor 5: Continuous Saturating Age Escalation (10%)**:
  $$P_{\text{age}}(\Delta t) = 100 \times \left(1 - \exp\left(-\frac{\Delta t}{72}\right)\right)$$
  Smoothly increases priority as SLA deadlines approach, reaching ~50 points at 50 hours and saturating at 100 points, preventing old tickets from suffering indefinite priority starvation.

### 4.2 Monte Carlo Rank Sensitivity Benchmark
- Evaluated rank stability across all $N=140$ seeded database reports over $M=200$ Monte Carlo simulations under uniform weight jitter up to $\pm 20\%$.
- Results on the $N=140$ dataset (`ml/eval/priority_sensitivity.py`):
  - $\pm 5\%$ Jitter: $\tau = 0.989$ (95% CI: [0.982, 0.995])
  - $\pm 10\%$ Jitter: $\tau = 0.980$ (95% CI: [0.970, 0.992])
  - $\pm 15\%$ Jitter: $\tau = 0.972$ (95% CI: [0.952, 0.987])
  - $\pm 20\%$ Jitter: $\tau = 0.962$ (95% CI: [0.934, 0.981])

> **Important Limitation**: This sensitivity analysis demonstrates **ranking stability under weight perturbations**, but does **NOT** prove the *correctness* of the priority ordering relative to ground-truth municipal dispatch urgency. All scoring weights ($w = [0.35, 0.25, 0.15, 0.15, 0.10]$) and POI bonuses are **expert-set heuristics, not learned from data**.

---

## 5. Duplicate Detection & Resolution Verification

### 5.1 Two-Tier Spatial Gating: Pre-Filter vs. Category Matching Radii
1. **Coarse Spatial Pre-Filter ($\le 50\text{m}$ / Bounding Box)**: Applied in SQL spatial queries to retrieve candidate active neighbor reports within the vicinity, avoiding full-table scans.
2. **Fine-Grained Per-Category Matching Thresholds**: Each candidate pair passing the 50m pre-filter is evaluated against its category-specific physical duplicate threshold ($15\text{m} - 35\text{m}$ base $+ 10\text{m}$ urban GPS accuracy margin):
   - *Pothole*: $20\text{m} + 10\text{m} = 30\text{m}$ max
   - *Road Damage*: $25\text{m} + 10\text{m} = 35\text{m}$ max
   - *Garbage Overflow*: $25\text{m} + 10\text{m} = 35\text{m}$ max
   - *Illegal Dumping*: $35\text{m} + 10\text{m} = 45\text{m}$ max
   - *Water Leakage*: $30\text{m} + 10\text{m} = 40\text{m}$ max
   - *Blocked Drain*: $25\text{m} + 10\text{m} = 35\text{m}$ max
   - *Broken Streetlight*: $35\text{m} + 10\text{m} = 45\text{m}$ max
   - *Damaged Infrastructure*: $25\text{m} + 10\text{m} = 35\text{m}$ max
   A candidate report at 38m passes the 50m spatial pre-filter but is rejected by the 30m pothole threshold. 50m is the coarse database pre-filter, whereas the per-category radius is the authoritative duplicate matching threshold.

### 5.2 Multimodal Duplicate Scoring & Statistical Reality
- **Composite Score**: Combines spatial distance score, category match, time decay ($e^{-\Delta t / 48\text{h}}$), and visual similarity (OpenCLIP ViT-B/32 cosine similarity or bitwise pHash fallback).
- **Missing Photo Handling**: Dynamically renormalizes remaining weights when visual evidence is unavailable.
- **Held-Out Test Results ($N=40$ test set with hard negatives, 50/50 validation/test split)**:
  - *Bitwise pHash*: Test Precision 58.1%, Recall 90.0%, F1 = 0.706 (95% CI: [0.542, 0.830]) at validation $\tau = 0.58$.
  - *OpenCLIP ViT-B/32*: Test Precision 65.5%, Recall 95.0%, F1 = 0.776 (95% CI: [0.622, 0.889]) at validation $\tau = 0.90$.
- **Statistical Interpretation**:
  - The pHash threshold of 0.58 is near chance agreement (~0.5) and likely reflects visual similarity among synthetic fixtures.
  - The 95% bootstrap confidence intervals for CLIP and pHash overlap substantially ([0.542, 0.830] vs. [0.622, 0.889]).
  - **No superiority claim is made**: embeddings cannot be claimed to statistically outperform bitwise pHash on this dataset.

### 5.3 Resolution Verification Engine
- **Spatial Proximity**: Distance $\le 50\text{m}$ between before and after capture coordinates.
- **Scene Consistency**: OpenCLIP embedding cosine similarity $\ge 55\%$.
- **Defect Disappearance**: Heuristic texture / defect disappearance verification.

---

## 6. Best-Effort Privacy Protection, Storage & Unredacted Originals

- **Image Storage Location**: Uploaded photos are stored on the server filesystem at `backend/uploads/` (mounted at `/app/uploads` in Docker) under UUID filenames.
- **In-Place Redaction & Non-Retention**: Unredacted upload bytes exist in transient server RAM during HTTP ingestion. The image is saved with EXIF/GPS metadata stripped, and `PrivacyService.anonymize_image()` performs an in-place overwrite on disk with Gaussian-blurred face pixels ($30\sigma$). The server **does NOT retain, archive, or serve unredacted original image files** once blurred.
- **Face Redaction Mechanism**: Bundled OpenCV Haar Cascade (`backend/app/ml/cascades/haarcascade_frontalface_default.xml`, licensed under BSD-3-Clause, Intel Corp / OpenCV Foundation). Frontal upright faces only; missed faces remain in the served image.
- **License Plate Redaction**: **NOT IMPLEMENTED**. Vehicle license plate redaction is explicitly omitted and not claimed. Any vehicle license plates in citizen photographs remain visible in stored and publicly served images.

---

## 7. Limitations, Biases & Ethical Considerations

1. **Physical Metric Depth Limitation**: Single-image depth or metric size estimation without physical fiducial markers is physically ill-posed. The platform models relative pixel bounding box coverage and dark pixel variance, explicitly disclaiming metric depth measurements to maintain scientific honesty.
2. **Synthetic Data Transparency**: All **140 seeded demo records** are marked with `is_synthetic=True` in the database, UI, and exports.
3. **Human-in-the-Loop Oversight**: Automated models assist municipal staff but do not make autonomous decisions regarding issue verification, ticket rejection, or contractor payment approval.
