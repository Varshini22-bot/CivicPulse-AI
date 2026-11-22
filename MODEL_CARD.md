# Model Card — CivicPulse AI Multi-Model Vision Architecture

## Model Overview
- **Project**: CivicPulse AI — Intelligent Civic Issue Detection & Decision Support
- **Architecture**: Modular Multi-Model Vision Pipeline (`CivicVisionPipeline`)
- **Components**:
  1. `HeuristicAnalyzer`: Classical Computer Vision (Sobel edge gradients, HSV color variance, dark pixel depth) + Rule-Based Keyword Scorer (Baseline).
  2. `RoadDefectDetector`: Localized defect detector for asphalt cracking and potholes (RDD2022 classes D00, D10, D20, D40) running via ONNX Runtime on CPU.
  3. `ZeroShotAnalyzer`: Vision-Language Foundation Model (OpenCLIP ViT-B/32) evaluating zero-shot prompts for municipal solid waste, drainage, and infrastructure defects.
- **Model Versions**:
  - `heuristic_analyzer` (v1.0.0)
  - `road_defect_detector` (`rdd2022-yolov8n-onnx-v1`)
  - `zeroshot_analyzer` (`openclip-vit-b-32-v1`)
- **Primary Frameworks**: PyTorch, Ultralytics YOLOv8, ONNX Runtime, OpenCLIP, OpenCV / PIL
- **License**: MIT (CivicPulse AI Application Code)

---

## Intended Use & Governance
- **Primary Use**: Automated defect categorization, localized bounding box detection, and municipal decision support for citizen-submitted civic reports in Bengaluru.
- **Target Users**: Municipal engineers, public works ward inspectors, dispatch coordinators, and civic administrators.
- **Authoritative Citizen Selection Policy**:
  - The citizen's submitted category is strictly **authoritative** and is never silently modified or overridden by the AI pipeline.
  - The AI pipeline produces transparent suggestions with calibrated confidence, bounding boxes, and explanation text.
  - If the AI suggests a different category with confidence $\ge 70\%$, the report is assigned `needs_human_verification` and surfaces an explanatory badge (`"AI suggests X"`) for municipal officer confirmation or rejection.
  - If confidence $< 40\%$ or if analyzers lack weights, the system safely triggers an **honest abstention** state rather than making arbitrary guesses.

---

## Datasets & Licensing

| Dataset | Modality | Annotations | Target Defect Classes | License | Role in CivicPulse |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RDD2022 (India)** | Dashcam RGB | Pascal VOC XML Bounding Boxes | D00 (Longitudinal), D10 (Transverse), D20 (Alligator), D40 (Pothole) | CC BY-SA 4.0 | Training detector for road surface defects |
| **OpenCLIP / LAION-2B** | Multimodal Web | Text-Image Pairs | Zero-Shot Municipal Prompts | MIT | Generalization across non-road categories |
| **TACO** | Mobile RGB | COCO JSON Bounding Boxes | Micro-litter (bottles, cups, cans) | CC BY 4.0 | Analyzed for domain gap (see below) |
| **OOD Bengaluru Benchmark** | Citizen Mobile | Categorical CSV | 8 Municipal Civic Issue Categories | Creative Commons (Curated) | Out-of-distribution evaluation set |

### TACO Domain Suitability Analysis
While the TACO (Trash Annotations in Context) dataset is widely referenced in computer vision for litter detection, analysis revealed a substantial domain gap for municipal operations:
1. **Scale**: TACO concentrates on individual micro-litter items (<2% frame area); municipal reports involve overflowing green dumpsters or multi-ton debris dumps (30%–85% frame area).
2. **Context**: TACO consists of parks, beaches, and suburban lawns; Bengaluru municipal issues occur adjacent to asphalt curbs, open stormwater drains, and construction sites.
3. **Actionability**: Detecting an individual soda can does not justify dispatching a municipal garbage compactor truck.
Consequently, CivicPulse AI uses calibrated OpenCLIP zero-shot classification for municipal waste triage rather than claiming false accuracy from TACO transfer.

### Ultralytics & Licensing Notice
The training pipeline supports Ultralytics YOLOv8n, licensed under **AGPL-3.0**. For commercial deployments requiring permissive non-copyleft licensing, the architecture supports dropping in **torchvision SSDLite MobileNetV3** (BSD-3-Clause) with zero interface modifications.

---

## Dashcam vs. Citizen Phone Domain Gap Analysis
RDD2022 images are captured via vehicle dashboard cameras:
- **Perspective**: Fixed height (~1.2m), horizontal pitch, fixed forward-facing angle.
- **Lighting**: Daytime road transit with vehicle hood glare.
- **Resolution & Focal Length**: Wide-angle vehicle lenses with fixed focal depth.

Citizen mobile phone uploads differ substantially:
- **Angle**: Steep overhead angles (looking down at potholes), oblique curb angles, extreme close-ups.
- **Lighting**: Nighttime phone flash, harsh monsoon overcast reflections, vehicle headlights.
- **Motion & Occlusion**: Hand shake, partial obstruction by pedestrian footwear, bicycles, or standing water.

To prevent overconfidence across this domain gap, the `CivicVisionPipeline` enforces confidence calibration and selective classification.

---

## Empirical Benchmark & Out-of-Distribution Results

Evaluated using `ml/eval/evaluate_ood.py` on the curated out-of-distribution Bengaluru fixture dataset (`data/ood_bengaluru/labels.csv`, $N=20$).

> [!NOTE]
> **Data Provenance & Disclaimer**:
> The 20 records in `labels.csv` and the images in `data/ood_bengaluru/images/` are synthetic fixture instances created to verify code paths and pipeline behavior. They are **not** real field photographs submitted by end users.
> **All metrics below represent a fixture smoke test only, not evidence of real-world model performance.** Real citizen photo collection and field evaluation is listed under "Needs user action".
> Metrics report exact statistical measurements with 95% Wilson Score confidence intervals for accuracy and 1,000-iteration bootstrap confidence intervals for Macro-F1.

### Mode 1: Image-Only Evaluation (True Visual Classifier Performance)
Evaluated with `image_path=path`, `description=""`, `user_hint=None` to eliminate label leakage and test pure visual representation:

| Analyzer | Accuracy | 95% Wilson CI | Macro F1 | 95% Bootstrap CI | Abstain Rate | Measured CPU Latency (p50) | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Heuristic Baseline** | 0.0% | [0.0%, 16.1%] | 0.000 | [0.000, 0.000] | 100.0% | 25.85 ms | Abstains honestly (Texture heuristics require text or high edge density) |
| **Road Defect Detector (RDD2022)** | 0.0% | [0.0%, 16.1%] | 0.000 | [0.000, 0.000] | 100.0% | 0.00 ms | Abstains honestly (Weights not placed in `weights/`) |
| **Zero-Shot CLIP (ViT-B/32)** | 10.0% | [2.8%, 30.1%] | 0.024 | [0.000, 0.052] | 0.0% | 802.73 ms | Active (Zero-shot OpenCLIP vision-language inference on CPU) |

### Mode 2: Multimodal Evaluation (Assisted Triage Pipeline)
Evaluated with `image_path=path`, `description=citizen_text`, `user_hint=None` to evaluate text-aided triage without leaking ground truth labels:

| Analyzer | Accuracy | 95% Wilson CI | Macro F1 | 95% Bootstrap CI | Abstain Rate | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Heuristic Baseline** | 75.0% | [53.1%, 88.8%] | 0.753 | [0.482, 0.850] | 20.0% | Active (Rule-based keyword extraction + texture verification) |
| **Road Defect Detector (RDD2022)** | 0.0% | [0.0%, 16.1%] | 0.000 | [0.000, 0.000] | 100.0% | Abstains honestly (Requires trained vision weights) |
| **Zero-Shot CLIP (ViT-B/32)** | 10.0% | [2.8%, 30.1%] | 0.024 | [0.000, 0.052] | 0.0% | Active (Evaluates image prompts directly) |

### Confidence Calibration & Real CPU Latency
Evaluated using `ml/eval/abstention_analysis.py`:
- **Expected Calibration Error (ECE)**: **Suppressed**. Standard ECE with 10 bins requires at least 50–100 samples per bin for statistically meaningful probability calibration. With $N=20$ total fixture samples, most bins have 0–2 samples, introducing extreme variance. ECE will be reported once a larger dataset ($N \ge 100$) is collected.
- **Measured End-to-End CPU Latency (Local Intel CPU, 10 warmups, 50 repetitions)**:
  - **HeuristicAnalyzer (Image-Only)**: p50: **25.85 ms** | p95: **31.08 ms** | p99: **34.28 ms** | mean: $25.46 \pm 3.87\text{ ms}$ (includes disk I/O, PIL decode, array conversion, Sobel/HSV extraction).
  - **RoadDefectDetector (Fallback)**: **0.00 ms** (instant graceful fallback).
  - **ZeroShotAnalyzer (OpenCLIP ViT-B/32)**: p50: **802.73 ms** | p95: **930.76 ms** | p99: **965.24 ms** | mean: $812.01 \pm 54.12\text{ ms}$ (full PyTorch ViT-B/32 image encode on CPU).

### Selective Classification Risk-Coverage Trade-Off (Multimodal Pipeline)
| Confidence Threshold ($\tau$) | Coverage | Selective Accuracy | Retained Samples | Abstained Samples |
| :---: | :---: | :---: | :---: | :---: |
| $\tau \ge 0.00$ | 100.0% | 45.0% | 20 | 0 |
| $\tau \ge 0.20$ | 100.0% | 45.0% | 20 | 0 |
| $\tau \ge 0.40$ | 95.0% | 42.1% | 19 | 1 |
| $\tau \ge 0.50$ | 70.0% | 21.4% | 14 | 6 |
| $\tau \ge 0.70$ | 60.0% | 16.7% | 12 | 8 |
| $\tau \ge 0.80$ | 50.0% | 20.0% | 10 | 10 |

---

## How to Train & Deploy Road Defect Weights
Because this development environment lacks a local CUDA GPU, complete training and export assets are provided:
1. **Google Colab Notebook**: Open `ml/notebooks/CivicPulse_Model_Training_Colab.ipynb` on a free T4 GPU instance.
2. **Execute Training**: Follow the turnkey cells to download RDD2022, train YOLOv8n with `seed=42`, verify PyTorch-to-ONNX numerical parity, and download `road_detector.onnx`.
3. **Deploy Locally**: Place `road_detector.onnx` into `backend/app/ml/weights/road_detector.onnx`. The `CivicVisionPipeline` automatically detects the weights file, switches `RoadDefectDetector` from `abstain` to `ok`, and starts rendering localized bounding boxes in the UI!

---

## Ethical & Governance Safeguards
- **No Autonomous Destruction/Closure**: AI classifications solely influence triage priority; they do not automatically reject, delete, or merge citizen submissions.
- **Audit Trails**: Every administrative override updates the database audit log and saves human feedback labels (`is_overridden=True`, `override_category_id`) for future model fine-tuning.
- **Privacy**: Uploaded images are stripped of EXIF metadata (GPS tags, device IDs) after computing spatial orientation and perceptual hashing. No facial recognition or biometric profiling is supported.
