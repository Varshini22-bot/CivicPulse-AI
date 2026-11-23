# Model Card — CivicPulse AI Multi-Model Decision Support Architecture

## 1. Model Overview

- **Project**: CivicPulse AI — Intelligent Civic Issue Detection, Prioritization & Resolution
- **Target Operational Context**: Municipal grievance redressal and public works dispatch in Bengaluru (BBMP, BWSSB, BESCOM).
- **Core Systems**:
  1. `CivicVisionPipeline`: Multi-model visual defect categorization and bounding box detection.
  2. `PriorityService` (v2): 5-factor calibrated priority scoring with continuous saturating age escalation and OpenStreetMap POI location risk.
  3. `DuplicateService` (v2): Multimodal duplicate detection combining spatial gating, OpenCLIP ViT-B/32 cosine similarity, bitwise pHash, and exponential time decay.
  4. `ResolutionVerificationService`: Automated before-and-after photo audit for municipal ticket closure verification.
  5. `PrivacyService`: Automated OpenCV Haar Cascade PII redaction for faces and license plates.
- **Model Versions**:
  - `heuristic_analyzer` (`v1.0.0`)
  - `road_defect_detector` (`rdd2022-yolov8n-onnx-v1`)
  - `zeroshot_analyzer` (`openclip-vit-b-32-v1`)
  - `priority_engine` (`v2.0.0`)
  - `resolution_verifier` (`v1.0.0`)
- **Primary Frameworks**: PyTorch, Ultralytics YOLOv8, ONNX Runtime, OpenCLIP, OpenCV, Scikit-Learn, Google OR-Tools.

---

## 2. Intended Use & Governance

- **Primary Application**: Municipal decision support for triaging citizen-reported infrastructure defects.
- **Authoritative Citizen Category Policy**:
  - Citizen category selection is strictly **authoritative**. Automated AI models suggest classifications but never silently override citizen intent without human review.
  - If visual confidence is high ($\ge 70\%$) and diverges from citizen input, the ticket is flagged as `needs_human_verification` for municipal officer confirmation.
  - If visual confidence is low ($< 40\%$) or trained weights are absent, the analyzer enters an **honest abstention** state rather than making unverified guesses.
- **Resolution Verification Policy Guard**:
  - Before-and-after photo verification audits ticket closures to detect fraudulent or incomplete repairs.
  - Policy Guard: The system **never auto-rejects** ticket closures. Suspicious or divergent pairs are flagged with status `flagged_for_review` for administrative supervisor review.

---

## 3. Computer Vision Pipeline Components

### 3.1 BaseAnalyzer Contract (`backend/app/ml/base.py`)
Standardized abstract interface returning:
- `analyzer_name`: Unique component name.
- `model_version`: SemVer string.
- `category_suggestion`: Predicted civic category code.
- `confidence`: Calibrated confidence in $[0.0, 1.0]$.
- `detections`: List of localized defect bounding boxes (`[ymin, xmin, ymax, xmax]`, class label, score).
- `explanation`: Human-readable natural language summary.
- `status`: Execution state (`ok`, `low_confidence`, `abstain`).

### 3.2 Component Breakdown
1. **HeuristicAnalyzer**:
   - Classical visual heuristics: Sobel edge gradient density, HSV color variance, and dark-pixel depth ratio.
   - Text heuristics: Keyword extraction with urgency weightings.
   - Execution time: ~2–5 ms on standard CPU.
2. **ZeroShotAnalyzer**:
   - Vision-language foundation model using OpenCLIP ViT-B/32.
   - Computes cosine similarity between candidate image embeddings and curated municipal prompt ensembles (e.g. `"a clear photo of an overflowing garbage container on a street"`, `"a photo of a burst water pipeline leaking clean water"`).
3. **RoadDefectDetector**:
   - Object detection architecture targeted at RDD2022 road defect classes (D00, D10, D20, D40).
   - Operates via ONNX Runtime on CPU with PyTorch fallback.
   - Enforces an explicit abstention contract: When trained model weights are not present in `models/`, the detector returns `status="abstain"` and allows the pipeline to rely transparently on the zero-shot and heuristic analyzers.

---

## 4. Priority Scoring v2 & Rank Stability

### 4.1 Five-Factor Calibrated Formula
$$\text{Priority} = 0.35 \times P_{\text{severity}} + 0.25 \times P_{\text{safety}} + 0.15 \times P_{\text{location}} + 0.15 \times P_{\text{community}} + 0.10 \times P_{\text{age}}$$

- **Factor 1: Physical Defect Severity (35%)**: Measures physical degradation intensity (1–10 mapped to 10–100) based on visual edge density, dark-pixel ratio, and defect area coverage. Decoupled from public safety.
- **Factor 2: Public Safety Hazard (25%)**: Evaluates danger to human life and vehicular traffic based on category hazard weights and acute danger keywords (e.g. "live wire", "open manhole").
- **Factor 3: Location Risk (15%)**: Geodesic proximity to 30 high-priority facilities (+35% for hospitals $\le 100\text{m}$, +30% for schools/transit $\le 100\text{m}$) using OpenStreetMap data.
- **Factor 4: Community Impact (15%)**: Citizen report frequency and upvotes ($15 \times \log_2(1 + N_{\text{upvotes}})$).
- **Factor 5: Continuous Saturating Age Escalation (10%)**:
  $$P_{\text{age}}(\Delta t) = 100 \times \left(1 - \exp\left(-\frac{\Delta t}{72}\right)\right)$$
  Smoothly increases priority as SLA deadlines approach, reaching ~50 points at 50 hours and saturating at 100 points, preventing old tickets from suffering indefinite priority starvation.

### 4.2 Monte Carlo Rank Sensitivity Benchmark
- Evaluated rank stability across $M=200$ simulations under uniform weight jitter up to $\pm 20\%$.
- Results demonstrated high stability (Kendall's $\tau \ge 0.955$):
  - $\pm 5\%$ Jitter: $\tau = 0.990$ (95% CI: [0.979, 0.996])
  - $\pm 10\%$ Jitter: $\tau = 0.978$ (95% CI: [0.963, 0.995])
  - $\pm 15\%$ Jitter: $\tau = 0.969$ (95% CI: [0.942, 0.989])
  - $\pm 20\%$ Jitter: $\tau = 0.955$ (95% CI: [0.917, 0.983])

> **Important Limitation**: This sensitivity analysis demonstrates **ranking stability under weight perturbations**, but does **NOT** prove the *correctness* of the priority ordering relative to ground-truth municipal dispatch urgency. All scoring weights ($w = [0.35, 0.25, 0.15, 0.15, 0.10]$) and POI bonuses are **expert-set heuristics, not learned from data**.

---

## 5. Duplicate Detection & Resolution Verification

### 5.1 Multimodal Duplicate Detection
- **Spatial Gate**: Hard category-specific radius ($15\text{m} - 35\text{m}$) with $10\text{m}$ urban GPS accuracy margin.
- **Visual Similarity**: OpenCLIP ViT-B/32 cosine similarity with 64-bit perceptual hash (pHash bitwise Hamming distance) fallback.
- **Time Proximity**: Smooth exponential decay ($e^{-\Delta t / 48\text{h}}$).
- **Missing Photo Handling**: Dynamically renormalizes remaining weights when visual evidence is unavailable.

### 5.2 Resolution Verification Engine
- **Spatial Proximity**: Distance $\le 50\text{m}$ between before and after capture coordinates.
- **Scene Consistency**: OpenCLIP embedding cosine similarity $\ge 55\%$.
- **Defect Disappearance**: Detector verifies absence of original defect.

---

## 6. Best-Effort Privacy Protection & PII Redaction

- **Mechanism**: OpenCV Haar Cascades (`haarcascade_frontalface_default.xml` and `haarcascade_russian_plate_number.xml`).
- **Processing**: Automatically applies Gaussian blur ($31 \times 31$ for faces, $25 \times 25$ for license plates) to citizen photo uploads before storage on a best-effort basis.
- **EXIF Sanitization**: Strips GPS coordinates and device serials while preserving physical image orientation via `ImageOps.exif_transpose`.
- **Limitation Notice**: Standard OpenCV cascades do NOT detect Indian-style vehicle registration plates (e.g. two-line motorcycle plates, yellow-board commercial plates) or non-frontal human faces. The feature is strictly best-effort.

---

## 7. Limitations, Biases & Ethical Considerations

1. **Physical Metric Depth Limitation**: Single-image depth or metric size estimation without physical fiducial markers is physically ill-posed. The platform models relative pixel bounding box coverage and dark pixel variance, explicitly disclaiming metric depth measurements to maintain scientific honesty.
2. **Synthetic Data Transparency**: All seeded demo records are marked with `is_synthetic=True` in the database, UI, and exports.
3. **Human-in-the-Loop Oversight**: Automated models assist municipal staff but do not make autonomous decisions regarding issue verification, ticket rejection, or contractor payment approval.
