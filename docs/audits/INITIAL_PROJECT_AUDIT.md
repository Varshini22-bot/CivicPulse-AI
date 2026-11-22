# CivicPulse AI — Initial Project Audit Report
**Date**: November 2026  
**Auditor**: Autonomous Senior Software Engineering Team  
**Scope**: Full Stack Inspection (Frontend, Backend, AI Pipeline, Spatial Engine, Database, Security, Tests)

---

## 1. Executive Summary

CivicPulse AI is an operational civic infrastructure decision-support platform. The application is designed to ingest citizen-reported infrastructure defects (potholes, road damage, garbage overflow, water leakage, blocked drains, broken streetlights, etc.), classify them through a Computer Vision feature pipeline, calculate an explainable 1–10 severity and 0–100 priority score, detect candidate duplicates via spherical Haversine distance and perceptual hashing, and route them to municipal engineering departments with immutable audit trails.

Overall State: **Functional Prototype with High Core Quality**, requiring visual and architectural modernization, security hardening, dark/light theme tokens, toast notifications, code splitting, and transparent documentation around AI benchmarking.

---

## 2. Feature-by-Feature Classification

| Feature Area | Classification | Status & Observations |
|---|---|---|
| **Authentication & Registration** | **Fully Implemented** | JWT tokens, Bcrypt password hashing, citizen registration, login, role-based RBAC (`citizen`, `admin`). Working and tested. |
| **Role-Based Authorization** | **Fully Implemented** | Server-side enforcement with `get_current_active_admin` on municipal dispatch and override routes. |
| **Citizen Report Submission** | **Fully Implemented** | Multipart form upload, image file extension validation, interactive Leaflet coordinate picker, address, area, multi-stage pipeline state simulation. |
| **Image Upload & Storage** | **Fully Implemented** | Stored in `/uploads` with unique UUID filenames; served statically via FastAPI StaticFiles. |
| **Computer Vision Classification** | **Fully Implemented (Hybrid)** | Real visual feature extraction (edge density via spatial diff, contrast, dark pixel ratio, HSV saturation, perceptual hash) blended with description keyword semantics. Uncertainty fallback for low confidence (<25%). |
| **Severity Estimation (1–10)** | **Fully Implemented** | Transparent multi-factor estimator taking base category severity + visual intensity (+1 to +2) + text safety threat (+1 to +3). Fully explainable. |
| **Priority Scoring Engine (0–100)** | **Fully Implemented** | Configurable 5-factor normalized formula (0.35 Severity + 0.25 Safety + 0.15 Location + 0.15 Community + 0.10 Age). Outputs Low/Medium/High/Critical with reasons. |
| **Duplicate Issue Detection** | **Fully Implemented** | Composite score: Haversine distance (45%) + category match (25%) + time proximity (15%) + visual hash Hamming similarity (15%). Flags candidates without destructive auto-merge. |
| **Duplicate Resolution Workflow** | **Fully Implemented** | Admins can confirm or reject duplicate links. Confirmed links assign canonical issue ID and log to audit trail. |
| **Geospatial Map (Leaflet)** | **Fully Implemented** | Color-coded markers (Critical: Red, High: Orange, Medium: Yellow, Low: Green), DBSCAN hotspot circles, interactive popups, coordinate picker. |
| **Hotspot Detection** | **Fully Implemented** | DBSCAN spatial density clustering ($\epsilon=800m$, Min=3) using radian coordinates and Haversine metric. |
| **Citizen Dashboard** | **Fully Implemented** | Real-time counts (Total, Under Review, In Progress, Resolved), filterable report list, report withdrawal modal. |
| **Admin Operations Dashboard** | **Fully Implemented** | 8 database-calculated KPIs, 4 Recharts visualizations (timeline trend, category breakdown, priority donut, turnaround time by category), ward filters. |
| **Issue Management Ledger** | **Fully Implemented** | Search, filter by category/priority/status/ward, sorting, pagination, status transition modal, department assignment modal. |
| **Issue Details Dossier** | **Fully Implemented** | Full report view, original photo, AI feature breakdown, probability distribution, human AI override modal, priority factor breakdown, map location, duplicate candidate actions, audit history. |
| **Municipal Status Transitions** | **Fully Implemented** | Strict state machine (`Submitted` → `Under Review` → `Verified` → `Assigned` → `In Progress` → `Resolved`/`Rejected`). Invalid transitions return HTTP 400. |
| **Audit Logging** | **Fully Implemented** | Immutable `audit_logs` table tracking user ID, action, previous state, new state, and timestamp on all status changes, overrides, and assignments. |
| **Notifications** | **Fully Implemented** | In-app notifications stored in database for report submission and status transitions. Mark read and mark all read endpoints. |
| **Analytics & BI** | **Fully Implemented** | Live SQL aggregations for KPIs and charts; no hardcoded static figures. |
| **CSV Export** | **Fully Implemented** | Real-time CSV generation via streaming response (`/api/analytics/export`) with query filters. |
| **Database Architecture** | **Fully Implemented** | SQLAlchemy 2.0 ORM with 11 entities. Supports PostgreSQL+PostGIS for production containers and SQLite with custom registered Haversine function for local zero-dependency development. |
| **Automated Test Suite** | **Fully Implemented** | 17 Pytest automated tests covering auth, submissions, CV, priority, duplicates, admin workflows, hotspots, and exports. 100% passing. |
| **Containerization** | **Fully Implemented** | Dockerfile for backend, Dockerfile for frontend with multi-stage Nginx build, and `docker-compose.yml` with PostgreSQL/PostGIS. |
| **AI Model Evaluation Transparency** | **Needs Improvement** | The 87.1% accuracy and confusion matrix currently rely on a synthetic 31-sample benchmark test vector. Needs clear documentation in `docs/AI_MODEL_EVALUATION.md` distinguishing between lightweight heuristic evaluation and real-world benchmark datasets. |
| **Dark Mode / Light Mode** | **Partially Implemented** | Primary navbar is dark navy; page content is light neutral. Lacks dynamic user theme toggle and theme persistence context. |
| **UI Polish & Modernization** | **Partially Implemented** | Needs toast notifications for async feedback, skeleton loading placeholders during data fetches, and image lightbox modals. |
| **Git Repository** | **Uninitialized** | Directory is not yet a Git repository. Needs initialization, `.gitignore`, `.env.example`, and commit history. |

---

## 3. Vulnerability & Code Quality Assessment

1. **Security**:
   - Passwords securely hashed with Bcrypt.
   - JWT tokens signed with HS256 and verified on every protected route.
   - Image uploads validate file extension (`.jpg`, `.jpeg`, `.png`, `.webp`) and use randomized UUID filenames to prevent path traversal attacks.
   - SQL queries use SQLAlchemy ORM parameterization, mitigating SQL injection risks.
   - Need to ensure CORS origins and secret keys are configurable via environment variables without hardcoded defaults in production.

2. **Code Maintainability**:
   - Backend modules are cleanly separated: `api/routes/`, `services/`, `models/`, `schemas/`, `ml/`, `core/`.
   - Frontend components use TypeScript interfaces and are organized into `components/ui/`, `components/layout/`, `components/maps/`, and `pages/`.
   - Frontend bundle is currently ~992 KB uncompressed. Code splitting via `React.lazy` can optimize load times.

---

## 4. Remediation & Modernization Action Plan

- **Phase 2**: Refactor services for clean dependency injection, add toast notifications and theme state context.
- **Phase 3 & 4**: Modern website redesign, adding dark/light mode toggle, skeleton loaders, toast feedback, and modal polish.
- **Phase 5 & 17**: Enhance AI pipeline honesty, detail feature extraction, and author comprehensive `docs/AI_MODEL_EVALUATION.md`.
- **Phases 6–16**: Verify severity, priority, duplicates, geospatial clustering, data pipelines, database safety, and realistic seed data.
- **Phases 18–25**: Automated tests, manual quality verification, documentation suite, Git repository setup, and final release review.
