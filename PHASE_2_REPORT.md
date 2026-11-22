# Phase 2 Completion Report: Real Computer Vision Pipeline & Verification

**Release Tag**: `v0.2.1`  
**Branch**: `phase-2-cv` -> merged into `main`  
**Execution Date**: November 22, 2026  
**Test Suite Status**: 37 Passed, 1 Skipped (PostGIS Docker only), 0 Failed  

---

## 1. Summary of Completed Work

Phase 2 established a modular, transparent, and ethically guarded Computer Vision architecture for CivicPulse AI, replacing arbitrary heuristics with a multi-model pipeline and rigorous evaluation protocols.

### Key Deliverables:
1. **Common Analyzer Contract (`backend/app/ml/base.py`)**:
   - `BaseAnalyzer` interface returning structured `AnalyzerResult` (model name, version, category suggestion, calibrated confidence, localized bounding boxes, human-readable evidence, and status: `ok`, `low_confidence`, `abstain`).
2. **Three Specialized Analyzers**:
   - `HeuristicAnalyzer`: Classical computer vision baseline extracting Sobel edge density, HSV saturation/value variance, and dark depression ratio with keyword filtering.
   - `RoadDefectDetector`: Localized road defect detector designed for RDD2022 (classes D00, D10, D20, D40) executing via ONNX Runtime on CPU. Safely abstains (`status="abstain"`) when local weights are not deployed.
   - `ZeroShotAnalyzer`: Vision-language foundation model using OpenCLIP (`ViT-B-32` / `laion2b_s34b_b79k`) executing zero-shot classification across civic prompt templates.
3. **Multi-Model Orchestrator (`backend/app/ml/pipeline.py`)**:
   - Enforces the **Authoritative Citizen Selection Policy**: The citizen's submitted category is **never** silently overwritten.
   - When AI confidence $\ge 0.70$ and suggests a different category, the issue is flagged with `needs_human_verification` and an explanatory suggestion badge for municipal review.
   - Honest abstention when confidence $< 0.40$ or when analyzers lack weights.
4. **Severity Integration & UI Overlays**:
   - `SeverityService` utilizes localized bounding box area and defect counts to refine the severity score.
   - `IssueDetailsPage.tsx` displays active analyzer badge, pipeline status (`OK` / `Low Confidence` / `Needs Human Review`), bounding boxes overlaid on citizen photos, and admin AI override workflow with database audit logging.
5. **Training Infrastructure**:
   - `ml/dataset.py`: Turnkey sequence-aware RDD2022 dataset preparation preventing dashcam frame leakage between splits.
   - `ml/train.py`: Turnkey Ultralytics YOLOv8 training script with ONNX export and PyTorch-to-ONNX numerical parity checks.
   - `ml/notebooks/CivicPulse_Model_Training_Colab.ipynb`: Ready-to-run Google Colab notebook for free T4 GPU execution.

---

## 2. Step 0: Verification & Corrections

Before finalizing Phase 2, an exhaustive verification of claims and metrics was performed:

### a) Data Provenance Disclosure
- **Finding**: The 20 records in `data/ood_bengaluru/labels.csv` and the generated images in `data/ood_bengaluru/images/` are synthetic fixture instances created to verify code paths and pipeline behavior. They are **not** real field photographs submitted by end users.
- **Correction**: All documentation, reports, and code comments were relabeled: **"Fixture smoke test only, not evidence of performance."** Real user photo collection is formally listed under "Needs user action".

### b) Root Cause of Heuristic 100% Accuracy (Label Leakage)
- **Finding**: The previous evaluation script passed the `notes` column containing ground truth keywords into `description`. The heuristic keyword matcher therefore had ground-truth leakage.
- **Correction**: `ml/eval/evaluate_ood.py` now evaluates both modes independently:
  - **Mode 1: Image-Only (True Visual Classifier Performance)** (`description=""`, `user_hint=None`): Heuristic accuracy is **0.0%** (95% CI: [0.0%, 16.1%]) with a **100% abstain rate** (honest texture heuristic behavior without text shortcuts).
  - **Mode 2: Multimodal (Assisted Triage Pipeline)** (`description=notes`, `user_hint=None`): Heuristic accuracy is **75.0%** (95% CI: [53.1%, 88.8%]) with a **20.0% abstain rate**.

### c) Root Cause of 0.02 ms Latency
- **Finding**: Previous latency benchmarking called `pipeline.process_report(image_path=None, ...)`, executing only in-memory string regexes in 0.02 ms and skipping all PIL decode and model inference.
- **Correction**: Re-measured real end-to-end CPU wall-clock latency per 640x480 image (file open, PIL decode, array conversion, model forward pass) on this machine (10 warmups, 50 timed repetitions):
  - **HeuristicAnalyzer (Image-Only)**: p50: **25.85 ms** | p95: **31.08 ms** | p99: **34.28 ms** | mean: $25.46 \pm 3.87\text{ ms}$
  - **RoadDefectDetector (Fallback)**: **0.00 ms** (instant graceful fallback)
  - **ZeroShotAnalyzer (OpenCLIP ViT-B/32)**: p50: **802.73 ms** | p95: **930.76 ms** | p99: **965.24 ms** | mean: $812.01 \pm 54.12\text{ ms}$

### d) Expected Calibration Error (ECE) Suppression
- **Finding**: Computing 10-bin ECE on $N=20$ samples is statistically uninformative because most bins hold 0–2 samples, creating extreme sampling variance.
- **Correction**: Headline ECE is explicitly suppressed in reports and `MODEL_CARD.md`, documenting the statistical requirement for $N \ge 50\text{--}100$ samples.

### e) Real OpenCLIP Verification
- **Finding**: OpenCLIP `ViT-B-32` (`laion2b_s34b_b79k`) was installed with CPU PyTorch and verified executing real image forward passes without crashing.

---

## 3. Measured Experimental Results

### Fixture Smoke Test Benchmark (`ml/eval/evaluate_ood.py`, $N=20$)

| Mode | Analyzer | Accuracy (95% Wilson CI) | Macro F1 (95% Bootstrap CI) | Abstain Rate | Status |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Image-Only** | Heuristic Baseline | 0.0% [0.0%, 16.1%] | 0.000 [0.000, 0.000] | 100.0% | Abstains honestly |
| **Image-Only** | Road Defect Detector | 0.0% [0.0%, 16.1%] | 0.000 [0.000, 0.000] | 100.0% | Abstains honestly (Weights not deployed) |
| **Image-Only** | Zero-Shot OpenCLIP | 10.0% [2.8%, 30.1%] | 0.024 [0.000, 0.052] | 0.0% | Active CPU inference |
| **Multimodal** | Heuristic Baseline | 75.0% [53.1%, 88.8%] | 0.753 [0.482, 0.850] | 20.0% | Active (Keyword + Texture) |
| **Multimodal** | Road Defect Detector | 0.0% [0.0%, 16.1%] | 0.000 [0.000, 0.000] | 100.0% | Abstains honestly |
| **Multimodal** | Zero-Shot OpenCLIP | 10.0% [2.8%, 30.1%] | 0.024 [0.000, 0.052] | 0.0% | Active CPU inference |

---

## 4. Test Suite Execution Output

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\varsh\Downloads\CivicPulse AI
configfile: pytest.ini
collected 38 items

backend/tests/test_admin_workflows.py::test_admin_list_reports PASSED    [  2%]
backend/tests/test_admin_workflows.py::test_admin_status_transitions PASSED [  5%]
backend/tests/test_admin_workflows.py::test_admin_ai_override PASSED     [  7%]
backend/tests/test_admin_workflows.py::test_geospatial_hotspots_and_markers PASSED [ 10%]
backend/tests/test_admin_workflows.py::test_analytics_and_export PASSED  [ 13%]
backend/tests/test_ai_pipeline.py::test_vision_classifier_text_heuristics PASSED [ 15%]
backend/tests/test_ai_pipeline.py::test_severity_estimator_critical_keywords PASSED [ 18%]
backend/tests/test_ai_pipeline.py::test_priority_service_scoring PASSED  [ 21%]
backend/tests/test_ai_pipeline.py::test_duplicate_service_haversine PASSED [ 23%]
backend/tests/test_ai_pipeline.py::test_duplicate_service_bitwise_hamming PASSED [ 26%]
backend/tests/test_ai_pipeline.py::test_model_evaluation_pipeline PASSED [ 28%]
backend/tests/test_auth.py::test_login_success PASSED                    [ 31%]
backend/tests/test_auth.py::test_login_invalid_credentials PASSED        [ 34%]
backend/tests/test_auth.py::test_citizen_registration PASSED             [ 36%]
backend/tests/test_auth.py::test_auth_me PASSED                          [ 39%]
backend/tests/test_ml_pipeline.py::test_base_analyzer_contract PASSED    [ 42%]
backend/tests/test_ml_pipeline.py::test_road_defect_detector_honest_abstention_without_weights PASSED [ 44%]
backend/tests/test_ml_pipeline.py::test_zeroshot_analyzer_abstention_on_missing_image PASSED [ 47%]
backend/tests/test_ml_pipeline.py::test_authoritative_citizen_selection_policy PASSED [ 50%]
backend/tests/test_ml_pipeline.py::test_severity_estimation_with_detection_box_metrics PASSED [ 52%]
backend/tests/test_ml_pipeline.py::test_ai_prediction_persistence_and_admin_feedback_loop PASSED [ 55%]
backend/tests/test_ml_pipeline.py::test_ml_evaluation_scripts_execute_cleanly PASSED [ 57%]
backend/tests/test_phase1_fixes.py::test_negative_rbac_citizen_forbidden PASSED [ 60%]
backend/tests/test_phase1_fixes.py::test_negative_rbac_unauthenticated_rejected PASSED [ 63%]
backend/tests/test_phase1_fixes.py::test_cors_headers_strict_origin PASSED [ 65%]
backend/tests/test_phase1_fixes.py::test_exif_gps_stripping_on_upload PASSED [ 68%]
backend/tests/test_phase1_fixes.py::test_exif_orientation_preserved_and_phash_aligned PASSED [ 71%]
backend/tests/test_phase1_fixes.py::test_bitwise_hamming_distance_exact PASSED [ 73%]
backend/tests/test_phase1_fixes.py::test_duplicate_weight_renormalization_missing_photo PASSED [ 76%]
backend/tests/test_phase1_fixes.py::test_category_specific_duplicate_radii PASSED [ 78%]
backend/tests/test_phase1_fixes.py::test_priority_orthogonality_no_double_counting PASSED [ 81%]
backend/tests/test_phase1_fixes.py::test_dynamic_data_driven_category_classification PASSED [ 84%]
backend/tests/test_phase1_fixes.py::test_data_provenance_is_synthetic PASSED [ 86%]
backend/tests/test_phase1_fixes.py::test_alembic_migrations_execute_cleanly PASSED [ 89%]
backend/tests/test_postgis_integration.py::test_postgis_migration_and_spatial_queries SKIPPED [ 92%]
backend/tests/test_reports.py::test_get_categories PASSED                [ 94%]
backend/tests/test_reports.py::test_submit_report_and_ai_processing PASSED [ 97%]
backend/tests/test_reports.py::test_get_my_reports PASSED                [100%]

================== 37 passed, 1 skipped in 97.22s (0:01:37) ===================
```

Frontend build:
```
✓ built in 1.80s
```

---

## 5. Deferred Items (Needs User Action)
1. **Model Weights Training (RDD2022 YOLOv8n)**:
   - Run `ml/notebooks/CivicPulse_Model_Training_Colab.ipynb` on Google Colab with a free T4 GPU.
   - Download the generated `road_detector.onnx` into `backend/app/ml/weights/road_detector.onnx`.
2. **Real Field Photograph Collection**:
   - Collect a calibrated dataset of genuine citizen mobile photographs across Bengaluru wards to replace fixture smoke tests with real field validation.
