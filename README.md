# CivicPulse AI

### Intelligent Civic Issue Detection, Geospatial Prioritization & Resolution Platform

[![CI/CD Pipeline](https://github.com/civicpulse/civicpulse-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/civicpulse/civicpulse-ai/actions)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![React 19](https://img.shields.io/badge/react-19-61dafb.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![PostGIS](https://img.shields.io/badge/PostGIS-16--3.4-336791.svg)](https://postgis.net/)
[![Tests Passing](https://img.shields.io/badge/tests-71%2F72%20passing-brightgreen.svg)](https://github.com/civicpulse/civicpulse-ai)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

---

## 🏛️ 1. Project Vision & Real-World Problem Statement

Rapidly expanding metropolitan regions face severe infrastructure monitoring challenges. In cities like Bengaluru, civic agencies (such as BBMP, BWSSB, and BESCOM) receive thousands of unstructured grievances daily. Municipal operations face critical bottlenecks:
- **Triage Delay**: Citizen complaints lack standardized categorization and severity estimation, causing acute hazards (e.g. open manholes, high-voltage wire collapses) to sit in unprioritized queues.
- **Duplicate Report Clutter**: Severe incidents generate dozens of duplicate reports from neighbors, overwhelming staff and obscuring newly reported defects.
- **Surface-Only Maintenance**: Repeatedly applying cosmetic asphalt patches to chronic failure corridors wastes public funds when systemic sub-base or drainage failures remain unaddressed.
- **Unverified Repairs**: Contractors can mark tickets resolved without empirical before-and-after photographic verification.

**CivicPulse AI** solves these challenges through an open, transparent, and explainable decision-support platform connecting citizens with municipal authorities.

---

## ⚠️ What This Project Does NOT Claim

To maintain scientific integrity and realistic operational expectations, this repository explicitly states:
1. **No Validated Accuracy on Real Citizen Photos**: The vision pipeline operates as an uncalibrated zero-shot prototype (OpenCLIP ViT-B/32) alongside classical texture heuristics; it has **not** been benchmarked or certified on a large-scale, field-collected dataset of real citizen grievance photos.
2. **No Real Municipal Data**: All 140 seeded complaints, citizen user records, and departmental assignments are synthetic demo fixtures generated for prototype demonstration.
3. **Advisory & Decision-Support Only**: Automated AI classifications, severity ratings, and duplicate detections are non-binding advisory suggestions designed to assist municipal engineers; the platform does not make autonomous administrative, legal, or contractor payment decisions.
4. **No Physical Metric Measurements**: The platform does **not** claim to measure physical pothole depth in centimeters or compute cubic volumetric repair estimates from single, uncalibrated 2D smartphone photographs.
5. **Best-Effort PII Redaction**: Face blurring uses the bundled OpenCV Haar cascade on a best-effort demonstration basis; license plate redaction is **not implemented** (standard cascades fail completely on Indian registration plates). See [`LIMITATIONS.md`](LIMITATIONS.md).

---

## 📐 2. System Architecture

```mermaid
flowchart TD
    subgraph CitizenClient["Citizen Mobile-First Portal (React 19 + TypeScript)"]
        CameraCapture["Camera Capture & GPS Readout"]
        AuthoritativeSelection["Authoritative Category Picker"]
        PreSubScan["Pre-Submission Duplicate Modal"]
        PublicTrack["Public Tracking (CP-YYYY-XXXX)"]
    end

    subgraph MunicipalAdmin["Municipal Operations Console"]
        TriageQueue["Priority v2 Triage Queue"]
        BulkAction["Bulk Status & Department Dispatch"]
        AuditQueue["Resolution Verification Audit (Side-by-Side)"]
        RouteOpt["Crew Route Optimization (Google OR-Tools)"]
        GISMap["Leaflet GIS Map (HDBSCAN / Chronic Corridors)"]
    end

    subgraph BackendAPI["FastAPI High-Throughput REST Engine (Python 3.11)"]
        RateLimiter["SlowAPI Rate Limiter"]
        AuthRBAC["Negative RBAC Middleware"]
        PrivacyEngine["OpenCV Haar Cascade Face Blurring (Plates Not Implemented)"]
        ExifSanitizer["EXIF GPS Purge & Orientation Transpose"]
    end

    subgraph SpatialIntelligence["Geospatial & Operations Research Engine"]
        HDBSCANEngine["HDBSCAN Spherical Clustering (Haversine Radians)"]
        OSMSnapping["OpenStreetMap Road Network Snapping"]
        ChronicCorridor["Chronic Defect Corridor & Engineering Advisories"]
        ORToolsTSP["Google OR-Tools TSP Dispatch Optimizer"]
    end

    subgraph MLEngine["Multi-Model Explainable Vision Pipeline"]
        HeuristicModel["HeuristicAnalyzer (Sobel, HSV, Dark Pixel)"]
        ZeroShotModel["ZeroShotAnalyzer (OpenCLIP ViT-B/32)"]
        DetectorModel["RoadDefectDetector (Not trained; abstains)"]
        PriorityV2["Priority v2 Engine (OSM POI Risk & Saturating Age)"]
        ResolutionVerifier["Resolution Verification Engine (CLIP Cosine + GPS)"]
    end

    subgraph Persistence["Storage & Database Layer"]
        PostgresPostGIS["PostgreSQL 16 + PostGIS (Geography Point & GiST)"]
        SQLiteFallback["SQLite + Haversine (Local Dev Fallback)"]
        MediaVault["Sanitized Photographic Vault"]
    end

    CitizenClient --> BackendAPI
    MunicipalAdmin --> BackendAPI
    BackendAPI --> MLEngine
    BackendAPI --> SpatialIntelligence
    SpatialIntelligence --> Persistence
    MLEngine --> Persistence
```

### 2.1 Embedding Storage & Scale-Up Path
Image embeddings (512-dimensional L2-normalized float vectors from OpenCLIP ViT-B/32) are serialized as raw JSON strings in the SQL database column `Report.embedding_json`. During duplicate checks and resolution audits, candidate reports within a spatial gate ($\le 50\text{m}$) are filtered via SQL spatial queries (PostGIS `ST_DWithin` / SQLite Haversine), and cosine similarity is computed in-memory in Python via NumPy dot products.

**Scale-Up Path (`pgvector`)**: For large-scale production deployments ($>10{,}000$ active reports), deserializing JSON embeddings into Python memory becomes a latency and memory bottleneck. Migrating embedding storage to PostgreSQL's native `pgvector` extension with HNSW or IVFFlat vector indexing is the established architectural scale-up path.

### 2.2 Two-Tier Spatial Gating: Bounding Box Pre-Filter vs. Category Matching Radii
To maintain high database query performance while adhering to physical defect boundaries, duplicate detection operates in two distinct tiers:
1. **Coarse SQL Spatial Bounding Box Pre-Filter**: Applied at the database query level ($\Delta \text{lat} = \pm 0.0025^\circ, \Delta \text{lon} = \pm 0.0025^\circ$, ~275 m) to retrieve candidate active neighbor reports within the vicinity, avoiding full-table scans while never prematurely pruning wide-radius categories (such as streetlights or pipe bursts).
2. **Fine-Grained Per-Category Duplicate Thresholds**: Once candidate records pass the coarse spatial pre-filter, each candidate pair is strictly evaluated against its specific physical category radius ($R_{\text{base}} + 10\text{m}$ urban GPS accuracy margin):
   - *Pothole*: $25\text{m} + 10\text{m} = \mathbf{35.0\text{m}}$ max
   - *Road Damage*: $35\text{m} + 10\text{m} = \mathbf{45.0\text{m}}$ max
   - *Garbage Overflow*: $30\text{m} + 10\text{m} = \mathbf{40.0\text{m}}$ max
   - *Illegal Dumping*: $40\text{m} + 10\text{m} = \mathbf{50.0\text{m}}$ max
   - *Water Leakage*: $75\text{m} + 10\text{m} = \mathbf{85.0\text{m}}$ max
   - *Blocked Drain*: $60\text{m} + 10\text{m} = \mathbf{70.0\text{m}}$ max
   - *Broken Streetlight*: $80\text{m} + 10\text{m} = \mathbf{90.0\text{m}}$ max
   - *Damaged Infrastructure*: $40\text{m} + 10\text{m} = \mathbf{50.0\text{m}}$ max
   - *Default / Uncategorized*: $100\text{m} + 10\text{m} = \mathbf{110.0\text{m}}$ max

A candidate pothole report at 38 m passes the SQL bounding box pre-filter but is **rejected** by the 35 m effective pothole threshold. The bounding box bounds SQL candidate retrieval, whereas the per-category radius ($R_{\text{eff}}$) is the authoritative duplicate matching threshold.

### 2.3 User Interface & Operational Workflows

The platform features a responsive React 19 + Tailwind CSS frontend supporting citizen grievance submission, public tracking, and municipal administrative triage. All views display a persistent amber demo banner communicating synthetic data provenance.

| Desktop Landing & Public Tracking | Citizen Mobile Report (375x812 Viewport) |
| :---: | :---: |
| ![Landing Page](docs/screenshots/landing.png) | ![Mobile Report View](docs/screenshots/report_mobile.png) |
| **Municipal Admin Triage Console** | **GIS Hotspots & Recurrence Clusters** |
| ![Admin Triage Console](docs/screenshots/admin_triage.png) | ![Map Hotspots](docs/screenshots/map_hotspots.png) |
| **Issue Detail & Explainable AI Panel** | **System Analytics & Model Performance** |
| ![Issue Detail AI Panel](docs/screenshots/issue_detail_ai.png) | ![Analytics Dashboard](docs/screenshots/analytics.png) |

---

## 🔬 3. Transparent AI & Machine Learning Engineering

### 3.1 Scientific Integrity: Removal of Fabricated Benchmarks
During Phase 1 of this project, forensic code inspection revealed a fabricated evaluation benchmark claiming "87.1% accuracy and 0.876 macro F1" generated from hardcoded 31-element static arrays. In accordance with honest engineering practices, these unsupported metrics were completely deleted from the codebase and documentation. 

Every performance metric cited in CivicPulse AI is produced by reproducible evaluation scripts executing within the repository.

### 3.2 Real Measured Benchmarks & Empirical Results

| Metric / Evaluation Target | Value | Reproducible Script | Significance |
| :--- | :--- | :--- | :--- |
| **Priority Rank Stability (Kendall's $\tau$)** | $\tau \in [0.962, 0.989]$ ($N=140$ reports) | `ml/eval/priority_sensitivity.py` | Confirms priority ordering is robust against weight jitter; shows stability, not correctness. |
| - *$\pm 5\%$ Jitter* | $\tau = 0.989$ (95% CI: [0.982, 0.995]) | `ml/eval/priority_sensitivity.py` | Very high stability |
| - *$\pm 10\%$ Jitter* | $\tau = 0.980$ (95% CI: [0.970, 0.992]) | `ml/eval/priority_sensitivity.py` | Very high stability |
| - *$\pm 15\%$ Jitter* | $\tau = 0.972$ (95% CI: [0.952, 0.987]) | `ml/eval/priority_sensitivity.py` | Very high stability |
| - *$\pm 20\%$ Jitter* | $\tau = 0.962$ (95% CI: [0.934, 0.981]) | `ml/eval/priority_sensitivity.py` | Very high stability |
| **Visual Duplicate Detection (OpenCLIP ViT-B/32)** | Precision: 65.5%, Recall: 95.0%, F1: 0.776 (95% CI: [0.622, 0.889]) | `ml/eval/evaluate_duplicates.py` | Labeled *synthetic fixtures, augmentation positives*. Evaluated on held-out test ($N=40$) with hard negatives; $\tau = 0.90$ tuned on val ($N=40$). |
| **Visual Duplicate Detection (Bitwise pHash)** | Precision: 58.1%, Recall: 90.0%, F1: 0.706 (95% CI: [0.542, 0.830]) | `ml/eval/evaluate_duplicates.py` | Validation threshold $\tau = 0.58$ is near chance (~0.5); CLIP vs pHash CIs overlap, so no superiority claim. |
| **Spatial Proximity Gate** | Bounding box pre-filter (~275m); Category Threshold ($35\text{m}-90\text{m}$) | `DuplicateService` | Coarse database retrieval pre-filter vs. fine-grained physical matching gate. |
| **Continuous Age Escalation** | $P_{\text{age}} = 100(1 - e^{-\Delta t/72})$ | `PriorityService` | Reaches ~50% at 50h, preventing low-priority ticket starvation (expert-set). |
| **Overall Backend Statement Coverage** | **79% Statement Coverage (72 Passed, 1 Skipped)** | `pytest backend/tests` | 77% to 95% statement coverage across core services. |
| **Frontend Component Test Coverage** | **85.1% Statement Coverage (5 Passed)** | `npm test --prefix frontend` | Vitest + JSDOM testing on critical components. |
| **Security Audits (`pip-audit`, `npm audit`)** | **0 Known Vulnerabilities** | `docs/SECURITY_AUDIT.md` | OWASP API Security Top 10 compliance verified. |

> **Note on Constants & Parameters**: All priority scoring weights ($w = [0.35, 0.25, 0.15, 0.15, 0.10]$), age half-life (72h), POI location bonuses (+35% hospital, +30% school/transit), duplicate base radii (25–80m base, 35–90m effective), and clustering eps (300m) are **expert-set, not learned from data**.

### 3.3 The BaseAnalyzer Contract & Honest Abstention
Every computer vision component implements the standardized `BaseAnalyzer` contract (`backend/app/ml/base.py`).

- **RoadDefectDetector**: Currently **not trained; abstains** until fine-tuned defect detection weights (`models/rdd2022_yolov8n.onnx`) are mounted. It emits `status="abstain"` on all citizen images, ensuring zero ungrounded detections.
- **ZeroShotAnalyzer**: Serves as a prototype zero-shot foundation model baseline using OpenCLIP ViT-B/32 prompt alignment, alongside classical texture heuristics (`HeuristicAnalyzer`). When visual confidence is below threshold ($< 35\%$), the analyzer abstains.
- **No Claims of Automated AI Defect Detection**: The system does **not** claim to provide an active, production-grade object detector for civic defects. A Colab training notebook is provided in `scripts/train_road_defect_detector.ipynb` for users wanting to train YOLOv8 on datasets like RDD2022 India.

### 3.4 Physical Metric Limitations
Estimating physical metric depth (e.g. pothole depth in centimeters) from an unconstrained 2D smartphone photo is an ill-posed inverse problem without camera intrinsic calibration or ground-plane fiducials. CivicPulse AI explicitly disclaims metric depth estimation, analyzing relative bounding box pixel coverage and dark-pixel variance instead.

---

## 🛠️ 4. Technology Stack

| Domain | Technology | Operational Role |
| :--- | :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS v4 | Responsive citizen reporting form, admin console, accessibility |
| **Mapping & GIS** | Leaflet 1.9, CartoDB Positron Tiles | Color-coded markers, accuracy circles, chronic corridor polylines |
| **Backend Framework** | FastAPI (Python 3.11), Uvicorn | Asynchronous REST API with automatic OpenAPI 3.1 documentation |
| **Database & ORM** | SQLAlchemy 2.0, Alembic, PostGIS / SQLite | Dual-database spatial compatibility, schema versioning |
| **Computer Vision** | PyTorch, ONNX Runtime, OpenCLIP ViT-B/32, OpenCV | Defect categorization, scene consistency, automated PII blurring |
| **Operations Research** | Google OR-Tools | Traveling Salesperson Problem (TSP) crew route optimization |
| **Clustering & Spatial** | Scikit-Learn HDBSCAN & DBSCAN | Spherical density clustering with exponential time decay |
| **Security & Auditing** | SlowAPI, PyJWT, Passlib (Bcrypt), pip-audit | Rate limiting, negative RBAC, EXIF stripping, supply chain defense |
| **Testing** | Pytest, Pytest-Cov, Vitest, Testing Library | 70 backend tests, 5 frontend component tests, CI/CD pipelines |

---

## 🚀 5. Quickstart & Installation

### 5.1 Prerequisites
- Python 3.11+
- Node.js 20+ & npm
- Docker & Docker Compose (Optional for containerized run)

### 5.2 Local Development Setup

#### Backend Setup
```bash
# 1. Clone repository
git clone https://github.com/civicpulse/civicpulse-ai.git
cd "CivicPulse AI"

# 2. Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install CPU PyTorch & backend dependencies
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r backend/requirements.txt

# 4. Initialize database migrations
cd backend
alembic upgrade head
python -m app.database.seed_data
cd ..

# 5. Start backend development server
uvicorn backend.app.main:app --reload --port 8000
```
Backend API interactive documentation is available at `http://localhost:8000/docs`.

#### Frontend Setup
```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start Vite dev server
npm run dev
```
Frontend application is accessible at `http://localhost:5173`.

### 5.3 Docker Compose Single-Command Launch
```bash
docker compose up --build
```
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- PostGIS Database: `localhost:5432`

---

## 🧪 6. Testing & Quality Assurance

### Run Backend Test Suite & Coverage
```bash
pytest backend/tests -v --cov=backend/app/services --cov=backend/app/ml --cov-report=term-missing
```

### Run Frontend Component Tests & Linter
```bash
npm test --prefix frontend
npm run lint --prefix frontend
npm run build --prefix frontend
```

### Run Security Audits
```bash
pip-audit -r backend/requirements.txt
npm audit --prefix frontend
```

---

## 🗺️ 7. Model Training in Google Colab

To train customized road defect detection models using public datasets:
1. Open the provided notebook: [`scripts/train_road_defect_detector.ipynb`](scripts/train_road_defect_detector.ipynb).
2. Connect to a free Google Colab T4 GPU instance.
3. Download the RDD2022 India road defect dataset or Roboflow defect annotations.
4. Execute training with Ultralytics YOLOv8n.
5. Export the trained weights to ONNX format: `model.export(format="onnx")`.
6. Place the resulting `rdd2022_yolov8n.onnx` file into `models/rdd2022_yolov8n.onnx`. CivicPulse AI will automatically detect the weights and switch from abstention mode to active object detection.

---

## ⚖️ 8. Ethics, Privacy & Data Provenance

- **Data Privacy & Image Storage**: All citizen uploads are stored in `backend/uploads/` (mounted at `/app/uploads` in Docker) under UUID filenames. Images undergo automated best-effort frontal face blurring via bundled OpenCV cascade (`haarcascade_frontalface_default.xml`, BSD-3-Clause) with in-place file overwrite. The server **does not retain or serve unredacted original images**. EXIF GPS coordinates and camera device serials are completely stripped prior to storage.
- **License Plate Limitation**: Vehicle license plate redaction is explicitly **not implemented**; any plates captured in citizen photos remain unredacted in the stored and served image files. Missed non-frontal faces also remain unblurred.
- **Data Provenance**: All **140 seeded records** are tagged with `is_synthetic=True`. The user interface displays a permanent demonstration disclaimer banner.
- **OpenStreetMap Data**: Road geometries and POIs are used under the **Open Database License (ODbL)**.
- **Human Governance**: Automated AI models produce explainable suggestions to support municipal officers; citizen input is authoritative and original complaints are never automatically deleted or merged.

---

## 📄 9. Documentation Index

- [User Handover & Operations Guide (`HANDOVER.md`)](HANDOVER.md)
- [System Limitations & Operational Boundaries (`LIMITATIONS.md`)](LIMITATIONS.md)
- [Comprehensive Code & AI Audit (`AUDIT.md`)](AUDIT.md)
- [Machine Learning Model Card (`MODEL_CARD.md`)](MODEL_CARD.md)
- [Dataset Provenance Card (`DATA_CARD.md`)](DATA_CARD.md)
- [Technical Interview Talking Points (`INTERVIEW_NOTES.md`)](INTERVIEW_NOTES.md)
- [5-Minute Demonstration Script (`DEMO_SCRIPT.md`)](DEMO_SCRIPT.md)
- [Security Audit & OWASP Top 10 Assessment (`docs/SECURITY_AUDIT.md`)](docs/SECURITY_AUDIT.md)

---

## 📜 10. License

CivicPulse AI is open-source software licensed under the [Apache License, Version 2.0](LICENSE).
