# CivicPulse AI — User Handover Guide

Welcome to **CivicPulse AI**! This document provides complete, turn-key instructions for running the project, performing model training on Google Colab, collecting and validating real-world Bengaluru photos, re-running evaluations, and recording a demonstration video.

---

## 1. Quick Local Execution

### Prerequisites
- Python 3.11+
- Node.js 20+

### Starting Backend & Frontend
1. **Backend**:
   ```powershell
   # In project root
   python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
   ```
2. **Frontend**:
   ```powershell
   npm run dev --prefix frontend -- --host localhost --port 5173
   ```
3. **Automated Verification**:
   ```powershell
   python scripts/verify_local_stack.py
   ```
   Runs a 13-point integration test verifying health, submission, public tracking, admin auth, KPIs, HDBSCAN hotspots, recurring failure corridors, OR-Tools routing, state transitions, resolution audits, and frontend delivery.

---

## 2. Model Training on Google Colab (GPU)

CivicPulse AI includes a zero-shot + heuristic CV pipeline that functions out-of-the-box. To replace heuristic abstentions with a real trained YOLOv8 road defect detector, train on a free Google Colab T4 GPU.

### Step-by-Step Instructions
1. Open Google Colab: [https://colab.research.google.com](https://colab.research.google.com).
2. Upload either notebook:
   - [`ml/notebooks/CivicPulse_Model_Training_Colab.ipynb`](ml/notebooks/CivicPulse_Model_Training_Colab.ipynb) or [`scripts/train_road_defect_detector.ipynb`](scripts/train_road_defect_detector.ipynb).
3. Set runtime to **GPU**:
   - Menu: `Runtime` -> `Change runtime type` -> select **T4 GPU** -> Save.
4. Run all cells in sequence:
   - **Dataset**: Automatically downloads the official RDD2022 India split (`https://bigdata.sekilab.global/cdd2022/RDD2022_India.tar.gz`, CC BY-SA 4.0).
   - **Classes**: Maps labels to 4 defect classes:
     - `D00`: Longitudinal Cracks
     - `D10`: Transverse Cracks
     - `D20`: Alligator Cracks
     - `D40`: Potholes
   - **Grouping**: Applies grouped sequence splitting by filename prefix (e.g. `India_0001`) to eliminate spatial/temporal data leakage between train and test splits.
   - **Training**: Fine-tunes `yolov8n.pt` for 30 epochs (expected runtime: **30–45 minutes** on T4 GPU).
   - **Export**: Exports weights to ONNX format with dynamic batching.
   - **Parity Check**: Validates $\max|y_{\text{pytorch}} - y_{\text{onnx}}| < 10^{-4}$ to ensure numerical consistency.
5. Download the exported weights:
   - Download `rdd2022_yolov8n.onnx` from the Colab file browser.
   - Place the file into your local repository at:
     ```
     models/rdd2022_yolov8n.onnx
     ```
6. Verify local detection:
   ```powershell
   pytest backend/tests/test_ml_pipeline.py -v
   ```
   The detector will automatically switch from honest abstention to real inference. For detailed troubleshooting, see [`ml/README_TRAINING.md`](ml/README_TRAINING.md).

---

## 3. Real-World Bengaluru Field Photography

The project currently ships with 20 synthetic benchmark fixtures. You can easily plug in real smartphone photos from Bengaluru to benchmark real-world performance.

### Collection Guidelines
- **Location & Safety**: Follow [`docs/PHOTO_GUIDE.md`](docs/PHOTO_GUIDE.md). Always prioritize pedestrian and traffic safety; photograph from safe sidewalks using high-visibility clothing.
- **Privacy First**: Do **not** capture recognizable human faces or readable vehicle number plates.
- **Defect Categories**: Focus on the 8 civic categories: `pothole`, `road_damage`, `garbage_overflow`, `illegal_dumping`, `water_leakage`, `blocked_drain`, `broken_streetlight`, `damaged_infrastructure`.
- **Target Count**: 20–50 photos (ideally $\ge 12$ photos per category for statistical validity).
- **Duplicate Pairs**: For testing duplicate detection, take 2 photos of the same defect from slightly different angles ($\Delta d \le 5\text{m}$) spaced 5–30 minutes apart.

### Dropping in Photos
1. Copy image files (`.jpg`, `.jpeg`, `.png`) into:
   ```
   data/ood_bengaluru_real/images/
   ```
2. Annotate images in [`data/ood_bengaluru_real/labels.csv`](data/ood_bengaluru_real/labels.csv):
   ```csv
   filename,category,severity,latitude,longitude,ward_id,timestamp
   IMG_0001.jpg,pothole,High,12.9345,77.6101,150,2026-11-23T10:00:00Z
   ```
3. Annotate duplicate/non-duplicate pairs in [`data/ood_bengaluru_real/pairs.csv`](data/ood_bengaluru_real/pairs.csv):
   ```csv
   image_a,image_b,is_duplicate,pair_type
   IMG_0001.jpg,IMG_0002.jpg,true,same_defect_different_angle
   IMG_0001.jpg,IMG_0003.jpg,false,hard_negative_nearby
   ```
4. Run the automated photo folder validation tool:
   ```powershell
   python scripts/validate_photo_folder.py
   ```
   Checks image readability, dimensions ($\ge 400\text{px}$), metadata schema, category balance, and warns of accidental near-duplicate shots.

---

## 4. Re-Running Evaluations & Updating Documentation

Once weights (`models/rdd2022_yolov8n.onnx`) or real photos (`data/ood_bengaluru_real/`) exist, update all benchmark evaluations with a single command:

```powershell
# Run the master evaluation runner
python ml/eval/run_all_evals.py
```

### Individual Evaluation Commands
- **Zero-Shot / Detector Classification Benchmark**:
  ```powershell
  python ml/eval/evaluate_ood.py --dataset real
  ```
  Writes results to `ml/eval/ood_benchmark_results_real.json`.
- **Duplicate Detection Benchmark (pHash vs. OpenCLIP)**:
  ```powershell
  python ml/eval/evaluate_duplicates.py --dataset real
  ```
  Writes results to `ml/eval/duplicate_benchmark_results_real.json`.
- **Priority Sensitivity Benchmark**:
  ```powershell
  python ml/eval/priority_sensitivity.py
  ```
- **Sync Documentation Tables**:
  ```powershell
  python scripts/sync_constants.py
  ```
  Automatically updates the synchronized tables in [`README.md`](README.md) and [`MODEL_CARD.md`](MODEL_CARD.md).

---

## 5. Demonstration Video Guide (2–3 Minutes)

Follow [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) for the visual storyboard and speaking points:

| Time | Scene | Workflow Demonstrated | Key Talking Point |
|---|---|---|---|
| **0:00–0:35** | Landing Page | Citizen grievance submission & pre-submission duplicate warning | Explain that duplicate warnings alert citizens before submitting redundant complaints, preserving municipal bandwidth. |
| **0:35–1:00** | Public Tracking | Unauthenticated tracking by tracking code (`CP-YYYY-XXXX`) | High-entropy tracking codes allow citizens to track complaint progress, SLA timers, and verification audits without login barriers. |
| **1:00–1:40** | Admin Dashboard | Triage queue, HDBSCAN GIS hotspot map, explainable AI | Multi-factor priority formula combines safety, school/hospital POI proximity, and saturating complaint age without double-counting. |
| **1:40–2:15** | Map & Routing | Google OR-Tools TSP crew dispatch route optimization | Automated traveling salesperson route sequencing reduces transit fuel and vehicle emissions for municipal repair crews. |
| **2:15–2:45** | Audit & Privacy | Human-in-the-loop resolution audit and PII face redaction | AI advises and audits, but human municipal engineers retain authoritative decision-making; PII is scrubbed before storage. |

---

## 6. Items Deferred to Future Releases & Architectural Rationale

In keeping with project integrity guidelines, the following items are intentionally deferred with explicit technical rationales:

1. **PostGIS Container in Local Windows Environment**:
   - *Current State*: Local development and tests use SQLite with Haversine distance and spatial bounding box indexing.
   - *Production State*: Alembic migrations (`geography(POINT, 4326)` and PostGIS GiST spatial index) and a dedicated PostGIS integration test (`test_postgis_integration.py`) are fully implemented and verified in Docker/GitHub Actions CI.
   - *Rationale*: Avoids requiring Docker Desktop installation for local evaluation and unit testing.
2. **License Plate Redaction**:
   - *Current State*: Automated face detection and blurring using OpenCV's frontal Haar cascade is implemented and verified.
   - *Deferred*: Vehicle license plate redaction.
   - *Rationale*: Indian vehicle license plate formats (HSRP, state fonts, commercial vs. private plates) vary widely across lighting and camera angles; without a dedicated fine-tuned plate detection model, simple Haar or rectangular heuristics yield unacceptable false-negative rates. The privacy service explicitly discloses best-effort face redaction only.
3. **Local Hardware YOLOv8 Training**:
   - *Current State*: Zero-shot OpenCLIP + heuristic classifier runs locally; CPU smoke test (`ml/train.py --smoke-run`) verifies the training and ONNX export pipeline.
   - *Rationale*: Training YOLOv8 on CPU is computationally intractable and would block local responsiveness. Turn-key Google Colab T4 GPU notebooks and instructions are provided instead.

---

## 7. Relevant References & Links

- **Main Overview**: [`README.md`](README.md)
- **Model Card & Transparency**: [`MODEL_CARD.md`](MODEL_CARD.md)
- **Data Provenance & Schema**: [`DATA_CARD.md`](DATA_CARD.md)
- **Known Limitations & Scope**: [`LIMITATIONS.md`](LIMITATIONS.md)
- **Claim-by-Claim Verification**: [`EVIDENCE.md`](EVIDENCE.md)
- **Field Photography Protocol**: [`docs/PHOTO_GUIDE.md`](docs/PHOTO_GUIDE.md)
- **Video Demo Storyboard**: [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md)
- **Portfolio & Resume Bullets**: [`RESUME_BULLETS.md`](RESUME_BULLETS.md)
