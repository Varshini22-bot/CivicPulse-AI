# CivicPulse AI — System Architecture Specification

## 1. High-Level Architectural Overview

CivicPulse AI is structured as a decoupled, multi-tier civic intelligence platform designed for municipal governments, public works agencies (BBMP, BWSSB, BESCOM), and urban citizens.

```
+-------------------------------------------------------------------------------+
|                                CLIENT TIER                                    |
|   React 19 + TypeScript + Vite + Tailwind CSS v4 + Lucide Icons + Recharts    |
|   - Citizen Grievance Portal & Interactive Defect Submission Form             |
|   - Municipal Operations Control Center & Paginated Ledger                    |
|   - GIS Spatial Intelligence Viewer (Leaflet OpenStreetMap)                   |
|   - Real-time Toast Notifications & System Dark / Light Theme Engine          |
+-------------------------------------------------------------------------------+
                                    |
                                    | REST APIs / JSON / JWT Bearer
                                    v
+-------------------------------------------------------------------------------+
|                               BACKEND TIER                                    |
|   FastAPI (Python 3.11) + Pydantic v2 + Uvicorn ASGI Server                   |
|   - Modular API Routers: /auth, /reports, /admin, /analytics, /map, /notif    |
|   - Security Layer: Argon2/Bcrypt Password Hashing, JWT RBAC, Magic-Bytes     |
|   - Service Layer: ReportService, PriorityService, DuplicateService, GeoSvc   |
+-------------------------------------------------------------------------------+
                                    |
                  +-----------------+-----------------+
                  |                                   |
                  v                                   v
+-----------------------------------+   +---------------------------------------+
|          AI & ML PIPELINE         |   |             DATA STORAGE              |
|  - Vision Classifier (Sobel/HSV)  |   |  - PostgreSQL 16 + PostGIS 3.4 (Prod) |
|  - Semantic Lexical Heuristics    |   |  - SQLite + Custom Haversine (Dev)    |
|  - 1–10 Defect Severity Estimator |   |  - SQLAlchemy 2.0 ORM                 |
|  - 5-Factor Priority Formula      |   |  - 9 Relational Entities              |
|  - DBSCAN Spatial Hotspot Engine  |   |  - Immutable Audit Log Ledger         |
+-----------------------------------+   +---------------------------------------+
```

---

## 2. Component Architecture

### 2.1 Frontend Architecture (`frontend/src/`)
- **Framework**: React 19 with TypeScript, bundled via Vite and styled with Tailwind CSS v4.
- **State Management & Contexts**:
  - `AuthContext.tsx`: JWT token lifecycle, login/logout, user roles (`citizen` vs `admin`).
  - `ThemeContext.tsx`: Dark/Light theme switching with OS system preference detection and `localStorage` persistence.
  - `ToastContext.tsx`: Reactive floating toast alert system for user feedback.
- **Routing**: Client-side reactive routing with `React.lazy` code splitting and `Suspense` fallback boundaries for all 10 core pages.
- **Geospatial Mapping**: Leaflet and React-Leaflet with custom SVG markers styled according to municipal priority urgency levels.

### 2.2 Backend Architecture (`backend/app/`)
- **API Entrypoint (`app/main.py`)**: Configures CORS middleware, registers modular APIRouters, initializes database tables, and mounts static file serving for uploaded defect evidence.
- **Authentication & Authorization (`app/core/security.py`, `app/api/deps.py`)**:
  - RFC 7519 JSON Web Tokens (JWT) signed using HS256 HMAC.
  - Role-Based Access Control (RBAC) ensuring citizen tokens cannot access administrative dispatch operations.
- **Business Service Layer (`app/services/`)**:
  - `ReportService`: Orchestrates issue ingestion, AI pipeline invocation, and state transitions.
  - `PriorityService`: Computes the 5-factor normalized 0–100 urgency score with factor breakdown and explainable reasons.
  - `DuplicateService`: Spherical Haversine distance calculations and candidate linking.
  - `GeospatialService`: Density-based DBSCAN clustering for municipal hotspots.

---

## 3. Data Flow & Transaction Lifecycle

1. **Submission**:
   - Citizen provides title, description, category, latitude, longitude, and optional photographic evidence.
   - API verifies file size (<10MB) and image magic bytes (Pillow raster verification).
2. **Automated AI Processing**:
   - `VisionClassifier` analyzes edge density and dark pixel cavity ratios.
   - `SeverityEstimator` derives 1–10 physical defect severity.
   - `PriorityService` calculates 0–100 urgency score across Severity, Safety, Location, Community, and Age.
   - `DuplicateService` runs Haversine query ($<100\text{m}$, $<30\text{ days}$) to identify matching complaints.
3. **Municipal Triage**:
   - Administrator reviews issue dossier in the Operations Control Center.
   - Officer can override AI classification or adjust severity (logged to `AuditLog`).
   - Officer dispatches report to relevant agency (BBMP, BWSSB, BESCOM) and field personnel.
4. **Resolution & Feedback**:
   - Status transitions to `In Progress` and ultimately `Resolved`.
   - Resolution proof photo and field notes recorded.
   - In-app notification delivered to citizen reporter.
