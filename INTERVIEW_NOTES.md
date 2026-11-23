# CivicPulse AI — Engineering Architecture & Technical Interview Guide

This guide is designed for technical portfolio walkthroughs, system design discussions, and coding interviews across AI/ML Engineering, Full-Stack Development, Data Engineering, and Product Operations.

---

## 1. Machine Learning & Computer Vision Architecture

### 1.1 The Multi-Model Analyzer Pattern
- **Architectural Decision**: Rather than coupling the API directly to a single model, CivicPulse AI implements a standardized abstract contract (`BaseAnalyzer`) in `backend/app/ml/base.py`.
- **Contract Signature**:
  - Every analyzer implements `analyze(image_path: str) -> AnalyzerResult`.
  - Returned dataclass exposes: `analyzer_name`, `model_version`, `category_suggestion`, `confidence`, `detections` (bounding boxes), `explanation`, and `status` (`ok`, `low_confidence`, `abstain`).
- **Ensemble Composition**:
  - `HeuristicAnalyzer`: Fast classical visual heuristics (Sobel gradients, HSV variance, dark-pixel ratio) + keyword scoring. Runs in <5ms without GPU.
  - `ZeroShotAnalyzer`: Vision-language embeddings using OpenCLIP ViT-B/32 comparing candidate image representations against category prompt ensembles.
  - `RoadDefectDetector`: Specialized object detector for road surface defects. Operates under an explicit abstention contract when trained weights are missing.

### 1.2 Honest Abstention vs. False Precision
- **Interview Talking Point**: Many student portfolios simulate machine learning by returning hardcoded 95% accuracy metrics or guessing classifications with low confidence.
- **CivicPulse Approach**: 
  - If visual confidence falls below the calibrated threshold ($< 40\%$) or if trained weights are absent, the analyzer explicitly emits `status="abstain"`.
  - The pipeline respects the citizen's category choice as authoritative. AI outputs are clearly flagged as suggestions, ensuring automated models never override citizen intent without municipal review.

### 1.3 Physical Metrics Limitation
- **Physical Reality**: Estimating true metric depth or centimeter pothole dimensions from an unconstrained single smartphone photo is ill-posed without camera intrinsics ($f_x, f_y$), ground tilt angle, or a physical fiducial reference.
- **Engineering Stance**: CivicPulse AI models relative pixel bounding box coverage and dark pixel variance, explicitly disclaiming metric depth measurements to maintain scientific honesty.

### 1.4 Resolution Verification Engine
- **Mechanism**: When field staff submit repair photos, `ResolutionVerificationService` conducts three independent audits:
  1. *Spatial Proximity*: Resolution GPS must be within 50 meters of the reported issue.
  2. *Scene Consistency*: OpenCLIP 512-dim visual embeddings must exhibit $\ge 55\%$ cosine similarity to confirm matching physical surroundings.
  3. *Defect Disappearance*: Vision detector confirms the original defect pattern is no longer visible.
- **Policy Guard**: Discrepancies flag tickets as `flagged_for_review` for supervisor audit rather than triggering automated rejection.

---

## 2. Geospatial Intelligence & Operations Research

### 2.1 PostGIS vs. SQLite Dual Compatibility
- **Deployment Topology**: PostgreSQL 16 with PostGIS extension. Uses `Geography(POINT, 4326)` columns indexed with spatial Generalized Search Trees (`GiST`), executing `ST_DWithin` queries for millimeter-accurate ellipsoidal spatial filtering.
- **Development Fallback**: SQLite with custom registered Python math functions for trigonometric Haversine distance, ensuring tests and local development run without external database daemons.

### 2.2 Spatial Clustering: HDBSCAN & DBSCAN
- **Coordinate Metric**: Standard Euclidean distance on raw latitude/longitude degrees produces severe geometric distortion away from the equator.
- **Mathematical Correction**: Coordinates are transformed to radians:
  $$\text{dist}_{\text{radians}} = \frac{\text{dist}_{\text{meters}}}{6{,}371{,}000}$$
  Clustering algorithms (HDBSCAN and DBSCAN) execute using the spherical `haversine` metric.
- **Temporal Weighting**: Active reports receive exponential decay weighting based on half-life parameters, giving recency priority to emerging defect clusters.

### 2.3 Chronic Defect Corridors & OSM Snapping
- **Snapping Algorithm**: Projects report coordinates onto line segments of the OpenStreetMap road network via perpendicular vector projection:
  $$t = \max\left(0, \min\left(1, \frac{(\mathbf{p} - \mathbf{a}) \cdot (\mathbf{b} - \mathbf{a})}{\|\mathbf{b} - \mathbf{a}\|^2}\right)\right)$$
- **Engineering Advisory**: When $\ge 3$ defects occur on the same road segment within 90 days, the platform flags a Chronic Defect Corridor and generates a civil engineering advisory (e.g., investigating sub-base drainage failure rather than repeatedly applying surface asphalt patches).

### 2.4 Dispatch Optimization with Google OR-Tools
- **Traveling Salesperson Problem (TSP)**: Solves optimal route traversal across open municipal tickets using OR-Tools constraint programming.
- **Cost Minimization**: Constructs an integer-meter distance matrix, minimizes total crew transit time at average urban speeds (18 km/h), accounts for 15-minute inspection dwell times, and outputs turn-by-turn stop sequences starting from municipal depot hubs.

---

## 3. Priority Scoring v2 & Rank Stability

### 3.1 Five-Factor Calibrated Formula
$$\text{Priority} = 0.35 \times P_{\text{severity}} + 0.25 \times P_{\text{safety}} + 0.15 \times P_{\text{location}} + 0.15 \times P_{\text{community}} + 0.10 \times P_{\text{age}}$$

- **Factor Separation**: Category safety hazard is decoupled from physical damage intensity to prevent double counting.
- **Continuous Saturating Escalation**:
  $$P_{\text{age}}(\Delta t) = 100 \times \left(1 - \exp\left(-\frac{\Delta t}{72}\right)\right)$$
  Smoothly increases priority as SLA deadlines approach, reaching ~50 points at 50 hours and saturating at 100 points, preventing old tickets from suffering indefinite priority starvation.
- **Geodesic Location Risk**: Incorporates 30 real Bengaluru high-priority POIs (+35% for hospitals $\le 100\text{m}$, +30% for schools/transit $\le 100\text{m}$).

### 3.2 Monte Carlo Sensitivity Validation
- Evaluated rank stability across $M=200$ simulations under uniform weight jitter up to $\pm 20\%$.
- Results demonstrated high stability (Kendall's $\tau \ge 0.955$), proving the prioritization system is robust against slight weight variations.

---

## 4. Full-Stack & Systems Architecture

### 4.1 Frontend (React 19, TypeScript, Leaflet)
- **Mobile-First Ingestion**: Camera input via `capture="environment"`, real GPS geolocation with accuracy readout and accuracy circle map rendering.
- **Pre-Submission Duplicate Scanner**: Before creating a report, checks existing issues within category radius; allows citizens to view and upvote existing tickets instead of cluttering the system.
- **Public Tracking**: Token-free status tracking via unique tracking numbers (`CP-YYYY-XXXX`) displaying an interactive 5-stage progression timeline.
- **Municipal Triage**: Multi-select bulk actions, filterable queues, and supervisor resolution audit views.

### 4.2 Security, RBAC & Hardening
- **SlowAPI Rate Limiting**: 30 requests/minute for report submissions; 10 requests/minute for authentication endpoints.
- **Negative RBAC**: Administrative endpoints and data export require admin role (`HTTP 403 Forbidden` for citizens).
- **Dual-Phase Evidence Sanitization**: Magic byte validation, EXIF metadata purge with physical orientation preserved, and OpenCV Haar Cascade blurring of faces and license plates.
- **Supply Chain**: 0 known vulnerabilities in `pip-audit` and `npm audit`.
