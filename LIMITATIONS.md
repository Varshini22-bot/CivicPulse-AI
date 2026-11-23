# CivicPulse AI — System Limitations & Operational Boundaries

This document provides a comprehensive, transparent inventory of the technical limitations, modeling assumptions, and operational boundaries of **CivicPulse AI**. It serves as an authoritative scientific disclaimer for municipal stakeholders, code reviewers, and technical interviewers.

---

## 1. Synthetic Fixtures & Benchmark Data Provenance

- **No Real Citizen Grievance Photos**: The 20 benchmark images in `data/ood_bengaluru/images/` and all test fixtures are synthetically generated image patterns (procedural textures, Perlin-like noise, color gradients, and geometric defects created via Pillow and NumPy). None of the images are real photographs captured on Bengaluru city streets.
- **Synthetic Database Records**: All 120 seeded complaints in the default database are synthetic demonstration records. Every synthetic ticket is marked with `is_synthetic = True` in the database, REST API payloads, UI triage screens, and CSV exports.
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

## 3. PII Redaction Scope: Faces Only, Plates NOT Implemented

- **Frontal Face Blurring (Best-Effort)**:
  - Automated privacy blurring uses the bundled OpenCV Haar Cascade (`backend/app/ml/cascades/haarcascade_frontalface_default.xml`, licensed under the 3-Clause BSD License by Intel Corporation and the OpenCV Foundation).
  - The model is loaded directly from the repository path and applies Gaussian blurring ($30\sigma$) to detected frontal human faces.
  - *Limitation*: The cascade only detects frontal, upright faces under adequate lighting; profile angles, tilted heads, occluded faces, and motion blur will be missed.
- **Vehicle License Plate Redaction (NOT IMPLEMENTED)**:
  - Standard OpenCV distributions only bundle cascades trained on single-line European or Russian GOST license plates.
  - These cascades completely fail on Indian vehicle registration plates (e.g. two-line motorcycle plates, yellow commercial transport boards, High Security Registration Plates [HSRP], and angled camera captures).
  - **CivicPulse AI explicitly does NOT implement vehicle license plate redaction.** No plate detection or blurring is performed or claimed.

---

## 4. No Real Municipal Administrative Integration

- **Simulated Agencies**: BBMP (Bruhat Bengaluru Mahanagara Palike), BWSSB (Bangalore Water Supply and Sewerage Board), and BESCOM (Bangalore Electricity Supply Company) department names, ward rosters, and SLA timelines are modeled strictly for demonstration purposes.
- **No Live Government API**: The platform is not connected to BBMP Sahaya, the Karnataka Government e-Parihara portal, or any live municipal ticketing system.
- **Non-Autonomous Decision Making**: The platform does not autonomously approve repair contracts, disburse public funds, or close citizen grievances. All actions require human municipal administrative review and confirmation.

---

## 5. Expert-Set Constants & Heuristic Parameters

All mathematical parameters, thresholds, and scoring weights in the platform are **heuristic constants set by engineering judgment**, not parameters learned from historical data:

| Parameter | Current Value | Nature | Operational Limitation |
| :--- | :--- | :--- | :--- |
| **Priority Component Weights** | $w = [0.35, 0.25, 0.15, 0.15, 0.10]$ | Heuristic | Relative importance of Severity, Risk, Impact, Recurrence, and Age is an uncalibrated policy assumption. |
| **Continuous Age Escalation Half-Life** | $72\text{ hours}$ ($P_{\text{age}} = 100(1 - e^{-\Delta t/72})$) | Heuristic | Reaches ~50% escalation at 50h; chosen to prevent starvation, not derived from empirical BBMP SLA data. |
| **POI Location Bonuses** | $+35\%$ (Hospital), $+30\%$ (School/Transit) $\le 100\text{m}$ | Heuristic | Fixed step bonus; does not model pedestrian density, peak transit hours, or patient ingress corridors. |
| **Duplicate Spatial Radii** | $15\text{m} - 35\text{m}$ category-dependent $+ 10\text{m}$ GPS margin | Heuristic | Fixed radii do not account for GPS multipath errors in dense high-rise urban canyons. |
| **DBSCAN / HDBSCAN $\varepsilon$** | $\varepsilon = 300\text{m}$, $\text{min\_samples} = 3$ | Heuristic | Tuned on synthetic spatial distributions; provisional default only. |

> **Sensitivity vs. Correctness**: While Monte Carlo simulations (`ml/eval/priority_sensitivity.py`) demonstrate high ranking stability under weight perturbations (Kendall's $\tau \ge 0.955$), stability under jitter does **not** prove that the priority ordering aligns with actual municipal triage urgency.

---

## 6. Physical Metric Depth & Volumetric Limitations

- **Inverse Problem**: Estimating physical depth (e.g. pothole depth in centimeters) or repair volume (e.g. cubic meters of asphalt) from an uncalibrated, unconstrained 2D smartphone photograph is physically ill-posed without camera intrinsic parameters, ground-plane fiducials, or stereo/LiDAR sensing.
- **CivicPulse AI Stance**: The system explicitly disclaims physical metric measurements. It evaluates visual severity using 2D pixel area bounding box ratios and dark-pixel shadow variance, clearly disclaiming centimeter depth estimates to uphold scientific integrity.

---

## 7. Vector Embedding Storage & Similarity Scalability

- **Storage Architecture**: Image embeddings (512-dimensional L2-normalized float vectors generated by OpenCLIP ViT-B/32) are serialized as raw JSON strings in the database column `Report.embedding_json`.
- **Search Mechanism**: Duplicate search performs spatial pre-filtering in SQL ($\le 50\text{m}$ radius gate) and then deserializes vectors into Python memory to compute cosine similarity using NumPy dot products.
- **Scale-Up Path (`pgvector`)**: For production deployments scaling beyond 10,000 active tickets, in-memory Python deserialization becomes a memory and latency bottleneck. Integrating the `pgvector` PostgreSQL extension with HNSW or IVFFlat vector indexing is the recommended architectural scale-up path.

---

## 8. RoadDefectDetector Abstention Contract

- **No Pre-Trained Weights**: The `RoadDefectDetector` (`backend/app/ml/road_defect_detector.py`) does **not** bundle pre-trained weights.
- **Abstention Contract**: When the model weight file (`models/rdd2022_yolov8n.onnx`) is absent, the detector strictly obeys the `BaseAnalyzer` contract and returns `status="abstain"`. It makes no predictions and incurs zero false positives.
- **Training Path**: A complete Google Colab training notebook is provided in [`scripts/train_road_defect_detector.ipynb`](scripts/train_road_defect_detector.ipynb) to allow users to train on public benchmarks (e.g. RDD2022 India) and mount their own weights.
