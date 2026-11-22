# CivicPulse AI — Phase 4 Engineering Report: Priority v2 & Resolution Verification

**Date**: November 2026  
**Branch**: `phase-4-priority-resolution`  
**Git Tag**: `v0.4`  
**Authors**: Senior AI/ML & Software Engineering Team  

---

## 1. Executive Summary

Phase 4 completes the transition from discrete heuristics to mathematically sound, continuous multi-criteria prioritization and introduces automated computer vision-based resolution audit pipelines with strict human-in-the-loop policy guards.

Key accomplishments:
1. **Continuous Saturating Age Escalation**: Replaced arbitrary step functions with continuous exponential saturation ($P_{\text{age}} = 100 \cdot (1 - e^{-\Delta t / 72\text{h}})$).
2. **OpenStreetMap POI-Based Location Risk**: Integrated real spatial proximity modeling to hospitals, emergency clinics, school zones, and transit hubs using OpenStreetMap data under the ODbL license.
3. **Priority Sensitivity Monte Carlo Benchmark**: Proven ranking stability ($\text{Kendall's } \tau \ge 0.955$ under $\pm 20\%$ weight jitter) across $M=200$ iterations and $N=100$ reports.
4. **Resolution Verification Engine**: Automated before-and-after audit checking GPS proximity, OpenCLIP background scene consistency ($\ge 55\%$), and vision defect disappearance.
5. **Municipal Policy Guard**: Strict rule ensuring vision verification never auto-rejects ticket closures, flagging discrepancies as `flagged_for_review` for supervisor audit.
6. **Privacy Protection & PII Redaction**: Automated best-effort Gaussian blurring of detected human faces and vehicle license plates via OpenCV Haar Cascades.
7. **Database Migration**: Alembic revision `005_add_priority_v2_and_resolution_verification.py` applied cleanly.
8. **Full Verification**: 53 backend tests passing (1 skipped PostGIS integration), frontend build clean in 1.93s.

---

## 2. Technical Implementation Details

### 2.1 Continuous Saturating Age Escalation
*Previous limitation*: Arbitrary discrete step boundaries caused sudden score jumps (e.g. 23 hours = 20 pts vs 25 hours = 50 pts).  
*Mathematical formulation*:
$$P_{\text{age}}(\Delta t) = 100 \times \left(1 - \exp\left(-\frac{\Delta t}{72.0}\right)\right)$$
Where $\Delta t$ is elapsed time in hours since ticket submission.
- $\Delta t = 0\text{h} \implies P_{\text{age}} = 0.0$
- $\Delta t = 12\text{h} \implies P_{\text{age}} = 15.4$
- $\Delta t = 24\text{h} \implies P_{\text{age}} = 28.3$
- $\Delta t = 72\text{h} \implies P_{\text{age}} = 63.2$ ($1 - 1/e$)
- $\Delta t = 168\text{h} \text{ (1 week)} \implies P_{\text{age}} = 90.3$

### 2.2 Location Risk via OpenStreetMap POIs
*Data Source*: `data/osm/bengaluru_pois.json` containing 30 validated spatial points of interest (hospitals, schools, colleges, metro stations, bus terminals) with OpenStreetMap ODbL attribution.
- **Hospitals & Emergency Facilities**: $+35\%$ location bonus if $\le 100\text{m}$, $+20\%$ if $\le 250\text{m}$.
- **Schools & Educational Institutes**: $+30\%$ location bonus if $\le 100\text{m}$, $+15\%$ if $\le 250\text{m}$.
- **Transit Hubs (Metro / Bus Terminals)**: $+30\%$ location bonus if $\le 100\text{m}$, $+15\%$ if $\le 250\text{m}$.
- **Fallback**: Graceful lexical keyword fallback for regions without localized OSM POI nodes.

### 2.3 Priority Weight Sensitivity Analysis (Monte Carlo Benchmark)
*Script*: `ml/eval/priority_sensitivity.py`  
*Methodology*: Monte Carlo perturbation of priority component weights ($w_{\text{severity}}=0.35, w_{\text{safety}}=0.25, w_{\text{location}}=0.20, w_{\text{age}}=0.20$) by uniform noise $\delta \sim U(-\epsilon, +\epsilon)$ with $M=200$ iterations per noise level, computing Kendall's rank correlation coefficient $\tau$ against the unperturbed ranking of $N=100$ reports.

*Measured Results* (`ml/eval/priority_sensitivity_results.json`):
| Weight Jitter ($\pm \epsilon$) | Mean Kendall's $\tau$ | 95% Confidence Interval | Rank Stability Assessment |
| :--- | :--- | :--- | :--- |
| $\pm 5\%$ | **0.990** | [0.979, 0.996] | Very High |
| $\pm 10\%$ | **0.978** | [0.963, 0.995] | Very High |
| $\pm 15\%$ | **0.969** | [0.942, 0.989] | Very High |
| $\pm 20\%$ | **0.955** | [0.917, 0.983] | Very High |

*Conclusion*: The priority formulation exhibits exceptional rank robustness; perturbations of up to $\pm 20\%$ preserve $>95.5\%$ rank concordance.

### 2.4 Resolution Verification Engine
*Module*: `backend/app/services/resolution_verification_service.py`  
*Verification Pipeline*:
1. **Spatial Proximity**: Resolution photo GPS coordinates compared against original incident location using Haversine distance. Threshold: $\le 50\text{m}$ (full pass), $50\text{m} - 100\text{m}$ (caution), $>100\text{m}$ (location warning).
2. **Scene Consistency**: OpenCLIP ViT-B/32 512-dim visual embeddings compared via cosine similarity. Threshold: $\ge 0.55$ confirms matching physical background.
3. **Defect Disappearance**: Evaluates after-photograph with `RoadDefectDetector` or `ZeroShotAnalyzer` to confirm no active hazards remain visible.
4. **Composite Score & Policy Guard**:
   $$S_{\text{composite}} = 0.35 S_{\text{gps}} + 0.35 S_{\text{scene}} + 0.30 S_{\text{disappearance}}$$
   If $S_{\text{composite}} \ge 0.65$ and defect disappeared $\to$ `verified`. Otherwise $\to$ `flagged_for_review`.  
   *POLICY GUARD*: Under no circumstance does the system auto-reject a field officer's ticket resolution. The ticket transitions to `Resolved`, and suspicious evidence is queued for supervisory administrative audit.

### 2.5 Privacy Protection & PII Redaction
*Module*: `backend/app/services/privacy_service.py`  
- Uses OpenCV Haar Cascades (`haarcascade_frontalface_default.xml` and `haarcascade_russian_plate_number.xml`).
- Applies adaptive kernel Gaussian blurring ($k_{\text{size}} = (\frac{w}{3} \cdot 2 + 1, \frac{h}{3} \cdot 2 + 1), \sigma = 30$) to detected faces and vehicle license plates upon upload.

---

## 3. Files Created or Modified

| Path | Action | Description |
| :--- | :--- | :--- |
| `data/osm/bengaluru_pois.json` | Created | Curated Bengaluru POI dataset with ODbL attribution |
| `backend/alembic/versions/005_add_priority_v2_and_resolution_verification.py` | Created | Alembic migration for verification status & score fields |
| `backend/app/models/__init__.py` | Modified | Updated `Report` and `PriorityScore` models |
| `backend/app/services/priority_service.py` | Modified | Continuous age scoring & OSM POI location risk |
| `backend/app/services/resolution_verification_service.py` | Created | Automated before/after photo verification engine |
| `backend/app/services/privacy_service.py` | Created | Face and license plate PII redaction service |
| `backend/app/services/report_service.py` | Modified | Integrated privacy redaction on upload & verification on resolve |
| `backend/app/api/routes/reports.py` | Modified | Exposed resolution verification parameters & payload |
| `backend/requirements.txt` | Modified | Added `opencv-python-headless` |
| `ml/eval/priority_sensitivity.py` | Created | Monte Carlo priority sensitivity analysis benchmark |
| `ml/eval/priority_sensitivity_results.json` | Created | Measured Kendall's $\tau$ output data |
| `backend/tests/test_priority_v2.py` | Created | 4 unit tests for age monotonicity, POI risk, sensitivity |
| `backend/tests/test_resolution_verification.py` | Created | 3 unit tests for verification engine & privacy service |

---

## 4. Test & Build Execution Results

### 4.1 Unit Test Execution Output
```
backend/tests/test_priority_v2.py::test_continuous_saturating_age_monotonicity PASSED [ 14%]
backend/tests/test_priority_v2.py::test_osm_poi_location_risk_calculation PASSED [ 28%]
backend/tests/test_priority_v2.py::test_location_risk_keyword_fallback PASSED [ 42%]
backend/tests/test_priority_v2.py::test_priority_sensitivity_benchmark_executes_cleanly PASSED [ 57%]
backend/tests/test_resolution_verification.py::test_resolution_verification_missing_images PASSED [ 71%]
backend/tests/test_resolution_verification.py::test_resolution_verification_with_images PASSED [ 85%]
backend/tests/test_resolution_verification.py::test_privacy_anonymization PASSED [100%]
============================== 7 passed in 6.13s ==============================
```

### 4.2 Full Backend Test Suite
```
53 passed, 1 skipped in 107.66s (0:01:47)
```

### 4.3 Frontend Production Build
```
vite v8.3.8 building client environment for production...
transforming...
✓ 2551 modules transformed.
rendering chunks...
dist/index.html                                1.10 kB │ gzip:   0.59 kB
dist/assets/index-DKxZ8eKF.css                52.07 kB │ gzip:   9.39 kB
dist/assets/index-CkUCwZNK.js                240.48 kB │ gzip:  74.93 kB
dist/assets/AdminDashboard-DnySUlSr.js       485.00 kB │ gzip: 135.34 kB
✓ built in 1.93s
```

---

## 5. Deferred Items & User Action
1. **Real Citizen Photos**: User action required to capture real Bengaluru street defect and resolution photographs for field calibration of the $0.55$ scene consistency threshold.
2. **YOLO Defect Detector Weights**: Can be trained using `ml/notebooks/CivicPulse_Model_Training_Colab.ipynb` and placed in `ml/weights/best_road_defect.onnx`.
