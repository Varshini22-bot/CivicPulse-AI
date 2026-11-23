# CivicPulse AI — System Limitations & Operational Boundaries

This document provides a comprehensive, transparent inventory of the technical limitations, modeling assumptions, and operational boundaries of **CivicPulse AI**. It serves as an authoritative scientific disclaimer for municipal stakeholders, code reviewers, and technical interviewers.

---

## 1. Synthetic Fixtures & Benchmark Data Provenance

- **No Real Citizen Grievance Photos**: The 20 benchmark images in `data/ood_bengaluru/images/` and all test fixtures are synthetically generated image patterns (procedural textures, Perlin-like noise, color gradients, and geometric defects created via Pillow and NumPy). None of the images are real photographs captured on Bengaluru city streets.
- **Synthetic Database Records**: All **140 seeded complaints** in the default database are synthetic demonstration records (135 base civic issues + 5 intentional duplicate cluster pairings across 12 Bengaluru localities). Every synthetic ticket is marked with `is_synthetic = True` in the database, REST API payloads, UI triage screens, and CSV exports.
- **Augmentation Positives**: The positive duplicate pairs used in `ml/eval/evaluate_duplicates.py` are generated using synthetic geometric and photometric data augmentations (random crops, perspective warping, brightness shifts, and rotations) applied to the base fixture images, rather than independently captured citizen photos of the same physical incident.

---

## 2. Zero-Shot OpenCLIP Out-of-Distribution (OOD) Accuracy

- **Empirical Measurement**: When evaluated strictly on **image embeddings alone** (disabling citizen text descriptions and category hints), OpenCLIP ViT-B/32 achieves only **10.0% top-1 accuracy (2/20 correct; 95% Wilson CI: [2.8%, 30.1%])** on the 20 synthetic fixtures across the 6 non-road civic categories:
  - *Garbage Overflow*: $1/3$ correct ($33.3\%$)
  - *Blocked Drain*: $1/3$ correct ($33.3\%$)
  - *Illegal Dumping*: $0/2$ correct ($0.0\%$)
  - *Water Leakage*: $0/2$ correct ($0.0\%$)
  - *Broken Streetlight*: $0/2$ correct ($0.0\%$)
  - *Damaged Infrastructure*: $0/2$ correct ($0.0\%$)
- **Operational Reality**: Off-the-shelf zero-shot vision-language foundation models cannot reliably categorize civic infrastructure failures without domain fine-tuning or citizen textual context.
- **System Design Consequence**: In CivicPulse AI, citizen category selection and multimodal descriptions are authoritative. The AI vision models serve purely as uncalibrated advisory baselines and consistency cross-checks; they do not override citizen input.

---

## 3. PII Redaction Scope, Storage & Unredacted Originals

- **Image Storage Location**:
  - Citizen uploads are stored on the server filesystem at `backend/uploads/` (mounted at `/app/uploads` in Docker) under UUID filenames (e.g. `uploads/<uuid>.jpg`).
- **In-Place Redaction & Non-Retention**:
  - Unredacted raw upload bytes exist only in transient server RAM during the HTTP request handler.
  - Images are saved to disk with EXIF/GPS metadata completely stripped by converting through pure PIL raster (`ImageOps.exif_transpose`).
  - When human faces are detected, `PrivacyService.anonymize_image()` performs an **in-place file overwrite** on disk with Gaussian-blurred pixel ROIs ($30\sigma$).
  - The server **does NOT retain, archive, or serve unredacted original image files** once blurred.
- **Frontal Face Blurring (Best-Effort)**:
  - Uses bundled OpenCV Haar Cascade (`backend/app/ml/cascades/haarcascade_frontalface_default.xml`, 3-Clause BSD License by Intel / OpenCV Foundation).
  - *Limitation*: The cascade only detects frontal, upright human faces under adequate lighting. Profile angles, tilted heads, occluded faces, and motion blur will be missed. Missed faces are NOT blurred and remain visible in the stored/served image.
- **Vehicle License Plate Redaction (NOT IMPLEMENTED)**:
  - Standard OpenCV cascades only provide models for single-line Russian/European GOST plates, which fail completely on Indian vehicle registration plates (two-line motorcycle plates, yellow commercial boards, HSRP plates, oblique camera angles).
  - **CivicPulse AI explicitly does NOT implement vehicle license plate redaction.** Any vehicle license plates present in citizen photographs remain unredacted in the stored and publicly served images.

---

## 4. No Real Municipal Administrative Integration

- **Simulated Agencies**: BBMP (Bruhat Bengaluru Mahanagara Palike), BWSSB (Bangalore Water Supply and Sewerage Board), and BESCOM (Bangalore Electricity Supply Company) department names, ward rosters, and SLA timelines are modeled strictly for demonstration purposes.
- **No Live Government API**: The platform is not connected to BBMP Sahaya, the Karnataka Government e-Parihara portal, or any live municipal ticketing system.
- **Non-Autonomous Decision Making**: The platform does not autonomously approve repair contracts, disburse public funds, or close citizen grievances. All actions require human municipal administrative review and confirmation.

---

## 5. Spatial Pre-Filter vs. Category Matching Radii & Expert Constants

All mathematical parameters, thresholds, and scoring weights in the platform are **heuristic constants set by engineering judgment**, not parameters learned from historical data:

### Two-Tier Spatial Gating: Pre-Filter vs. Threshold
To maintain database query efficiency while enforcing physical defect boundaries, duplicate detection operates in two distinct stages:
1. **Coarse Spatial Pre-Filter ($\le 50\text{m}$ / Bounding Box)**: Applied at the SQL query level (PostGIS `ST_DWithin` / bounding box coordinate range) to select candidate active neighbor reports without executing full table scans.
2. **Fine-Grained Per-Category Matching Threshold ($15\text{m} - 35\text{m} + 10\text{m}$ GPS margin)**: Once candidates pass the 50m pre-filter, each pair is strictly evaluated against its specific category radius (e.g. pothole $\le 20\text{m} + 10\text{m} = 30\text{m}$ max; broken streetlight $\le 35\text{m} + 10\text{m} = 45\text{m}$ max). A candidate at 38m will pass the 50m spatial pre-filter but be **rejected** by the pothole matching threshold. There is no contradiction: 50m is the coarse database retrieval pre-filter, while the per-category radius is the authoritative duplicate matching threshold.

### Heuristic Constants Summary

| Parameter | Current Value | Nature | Operational Limitation |
| :--- | :--- | :--- | :--- |
| **Priority Component Weights** | $w = [0.35, 0.25, 0.15, 0.15, 0.10]$ | Heuristic | Relative importance of Severity, Risk, Impact, Recurrence, and Age is an uncalibrated policy assumption. |
| **Continuous Age Escalation Half-Life** | $72\text{ hours}$ ($P_{\text{age}} = 100(1 - e^{-\Delta t/72})$) | Heuristic | Reaches ~50% escalation at 50h; chosen to prevent starvation, not derived from empirical BBMP SLA data. |
| **POI Location Bonuses** | $+35\%$ (Hospital), $+30\%$ (School/Transit) $\le 100\text{m}$ | Heuristic | Fixed step bonus; does not model pedestrian density, peak transit hours, or patient ingress corridors. |
| **Duplicate Category Base Radii** | $15\text{m} - 35\text{m}$ category-dependent $+ 10\text{m}$ GPS margin | Heuristic | Fixed radii do not account for GPS multipath errors in dense high-rise urban canyons. |
| **DBSCAN / HDBSCAN $\varepsilon$** | $\varepsilon = 300\text{m}$, $\text{min\_samples} = 3$ | Heuristic | Tuned on synthetic spatial distributions; provisional default only. |

> **Sensitivity vs. Correctness**: While Monte Carlo simulations (`ml/eval/priority_sensitivity.py`) across all $N=140$ seeded reports demonstrate high ranking stability under weight perturbations (Kendall's $\tau \ge 0.962$ under $\pm 20\%$ jitter), stability under jitter does **not** prove that the priority ordering aligns with actual municipal triage urgency.

---

## 6. Duplicate Benchmark Statistical Reality: Overlapping Confidence Intervals

- **Held-Out Test Results ($N=40$, 50/50 Validation/Test Split with Hard Negatives)**:
  - Bitwise pHash: Test F1 = 0.706 (95% CI: [0.542, 0.830]) at validation-tuned threshold $\tau = 0.58$.
  - OpenCLIP ViT-B/32: Test F1 = 0.776 (95% CI: [0.622, 0.889]) at validation-tuned threshold $\tau = 0.90$.
- **Statistical Interpretation**:
  - The pHash threshold of 0.58 is near chance agreement (~0.5) and likely reflects visual similarity among synthetic fixtures rather than robust edge correlation.
  - The 95% bootstrap confidence intervals for OpenCLIP and pHash overlap substantially ([0.542, 0.830] vs. [0.622, 0.889]).
  - **No superiority claim is made**: OpenCLIP embeddings cannot be claimed to statistically outperform bitwise pHash on this dataset.

---

## 7. Physical Metric Depth & Volumetric Limitations

- **Inverse Problem**: Estimating physical depth (e.g. pothole depth in centimeters) or repair volume (e.g. cubic meters of asphalt) from an uncalibrated, unconstrained 2D smartphone photograph is physically ill-posed without camera intrinsic parameters, ground-plane fiducials, or stereo/LiDAR sensing.
- **CivicPulse AI Stance**: The system explicitly disclaims physical metric measurements. It evaluates visual severity using 2D pixel area bounding box ratios and dark-pixel shadow variance, clearly disclaiming centimeter depth estimates to uphold scientific integrity.

---

## 8. Vector Embedding Storage & Similarity Scalability

- **Storage Architecture**: Image embeddings (512-dimensional L2-normalized float vectors generated by OpenCLIP ViT-B/32) are serialized as raw JSON strings in the database column `Report.embedding_json`.
- **Search Mechanism**: Duplicate search performs spatial pre-filtering in SQL ($\le 50\text{m}$ radius gate) and then deserializes vectors into Python memory to compute cosine similarity using NumPy dot products.
- **Scale-Up Path (`pgvector`)**: For production deployments scaling beyond 10,000 active tickets, in-memory Python deserialization becomes a memory and latency bottleneck. Integrating the `pgvector` PostgreSQL extension with HNSW or IVFFlat vector indexing is the recommended architectural scale-up path.

---

## 9. RoadDefectDetector Abstention Contract

- **No Pre-Trained Weights**: The `RoadDefectDetector` (`backend/app/ml/road_defect_detector.py`) does **not** bundle pre-trained weights.
- **Abstention Contract**: When the model weight file (`models/rdd2022_yolov8n.onnx`) is absent, the detector strictly obeys the `BaseAnalyzer` contract and returns `status="abstain"`. It makes no predictions and incurs zero false positives.
- **Training Path**: A complete Google Colab training notebook is provided in [`scripts/train_road_defect_detector.ipynb`](scripts/train_road_defect_detector.ipynb) to allow users to train on public benchmarks (e.g. RDD2022 India) and mount their own weights.
