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

Evaluated using `ml/eval/evaluate_ood.py` on the curated out-of-distribution Bengaluru citizen dataset (`data/ood_bengaluru/labels.csv`, $N=20$).

> [!NOTE]
> Single-annotator out-of-distribution benchmark set ($N=20$). Metrics report exact statistical measurements with 95% Wilson Score confidence intervals for accuracy and 1,000-iteration bootstrap confidence intervals for Macro-F1.

| Analyzer | Accuracy | 95% Confidence Interval | Macro F1 | 95% Bootstrap CI | Abstain Rate | Measured CPU Latency (p50) | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Heuristic Baseline** | 100.0% | [83.9%, 100.0%] | 1.000 | [0.750, 1.000] | 0.0% | 0.02 ms | Deployed (Rule-Based Baseline) |
| **Road Defect Detector (RDD2022)** | — | — | — | — | 100.0% | — | Abstains honestly (Local weights not loaded) |
| **Zero-Shot CLIP (ViT-B/32)** | — | — | — | — | 100.0% | — | Abstains honestly (Requires image input) |

### Confidence Calibration & Latency
Evaluated using `ml/eval/abstention_analysis.py`:
- **Expected Calibration Error (ECE)**: $0.545$ (reflecting underconfidence in heuristic keyword matches relative to 100% discrete bin scores).
- **Inference Latency (Local Intel CPU)**:
  - **Median (p50)**: $0.02\text{ ms}$ (text keyword inference) / $\sim 15\text{ ms}$ (full PIL statistical image analysis)
  - **95th Percentile (p95)**: $0.02\text{ ms}$
  - **Minimum**: $0.01\text{ ms}$
  - **Maximum**: $0.18\text{ ms}$

### Risk-Coverage Trade-Off (Selective Classification)
| Confidence Threshold ($\tau$) | Coverage | Selective Accuracy | Retained Samples | Abstained Samples |
| :---: | :---: | :---: | :---: | :---: |
| $\tau \ge 0.00$ | 100.0% | 100.0% | 20 | 0 |
| $\tau \ge 0.30$ | 100.0% | 100.0% | 20 | 0 |
| $\tau \ge 0.40$ | 50.0% | 100.0% | 10 | 10 |
| $\tau \ge 0.60$ | 0.0% | 100.0% | 0 | 20 |

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
