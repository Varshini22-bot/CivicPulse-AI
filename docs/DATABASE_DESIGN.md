# CivicPulse AI — Database Schema & Architecture Design

## 1. Relational Entity Overview

CivicPulse AI utilizes a normalized relational data model managed through SQLAlchemy 2.0 ORM. The architecture supports:
- **Production Tier**: PostgreSQL 16 with PostGIS 3.4 spatial extensions and spatial R-Tree / GiST indexing.
- **Local Development / Embedded Tier**: SQLite 3 with deterministic user-registered spherical math functions (`haversine_meters`) providing seamless local execution without requiring database daemon dependencies.

```
+-----------------------------------------------------------------------------------------+
|                                    ENTITY RELATIONSHIPS                                 |
+-----------------------------------------------------------------------------------------+

   [User] 1 -------- * [Report] (citizen_id)
      |                    |
      |                    +------- 1 ------- 1 [AIPrediction]
      |                    |
      |                    +------- 1 ------- 1 [PriorityScore]
      |                    |
      |                    +------- 1 ------- * [DuplicateCandidate] (source/target)
      |                    |
      |                    +------- 1 ------- * [Assignment] (report_id)
      |                    |                        |
      |                    |                        +------ * --- 1 [Department]
      |                    |                        +------ * --- 1 [Staff]
      |                    |
      |                    +------- 1 ------- * [AuditLog] (report_id)
      |
      +-------- 1 -------- * [Notification] (user_id)

   [Category] 1 ----------- * [Report] (category_id, verified_category_id)
```

---

## 2. Table Specifications

### 2.1 `users`
Represents citizens, field staff, and municipal administrators.
- `id` (VARCHAR(36), PK, UUIDv4)
- `email` (VARCHAR(255), UNIQUE, NOT NULL, Indexed)
- `hashed_password` (VARCHAR(255), NOT NULL)
- `full_name` (VARCHAR(255), NOT NULL)
- `role` (VARCHAR(50), NOT NULL, Default: `'citizen'`) — Values: `'citizen'`, `'admin'`, `'inspector'`
- `is_active` (BOOLEAN, Default: `True`)
- `phone` (VARCHAR(50), NULL)
- `created_at` (TIMESTAMP WITH TIME ZONE, Default: `utcnow`)

### 2.2 `departments`
Municipal governing divisions and statutory boards (e.g. BBMP, BWSSB, BESCOM).
- `id` (VARCHAR(36), PK, UUIDv4)
- `name` (VARCHAR(255), UNIQUE, NOT NULL)
- `code` (VARCHAR(50), UNIQUE, NOT NULL)
- `contact_email` (VARCHAR(255), NULL)
- `phone` (VARCHAR(50), NULL)
- `description` (TEXT, NULL)

### 2.3 `staff`
Municipal engineers, field technicians, and rapid response personnel.
- `id` (VARCHAR(36), PK, UUIDv4)
- `department_id` (VARCHAR(36), FK -> `departments.id`, NOT NULL)
- `name` (VARCHAR(255), NOT NULL)
- `email` (VARCHAR(255), NOT NULL)
- `phone` (VARCHAR(50), NULL)
- `role_title` (VARCHAR(100), NOT NULL)
- `is_available` (BOOLEAN, Default: `True`)

### 2.4 `categories`
Taxonomy of civic infrastructure defect types.
- `id` (VARCHAR(36), PK, UUIDv4)
- `code` (VARCHAR(50), UNIQUE, NOT NULL, Indexed) — e.g. `'pothole'`, `'garbage_overflow'`
- `name` (VARCHAR(100), NOT NULL)
- `description` (TEXT, NULL)
- `icon` (VARCHAR(50), NULL)
- `base_severity_weight` (FLOAT, Default: `5.0`)

### 2.5 `reports`
Central grievance ledger tracking civic issues.
- `id` (VARCHAR(36), PK, UUIDv4)
- `tracking_number` (VARCHAR(50), UNIQUE, NOT NULL, Indexed) — Format: `CP-2026-XXXXX`
- `citizen_id` (VARCHAR(36), FK -> `users.id`, NULL, OnDelete: SET NULL)
- `title` (VARCHAR(255), NOT NULL)
- `description` (TEXT, NOT NULL)
- `category_id` (VARCHAR(36), FK -> `categories.id`, NOT NULL)
- `verified_category_id` (VARCHAR(36), FK -> `categories.id`, NULL)
- `latitude` (FLOAT, NOT NULL, Indexed)
- `longitude` (FLOAT, NOT NULL, Indexed)
- `address` (TEXT, NULL)
- `area` (VARCHAR(100), NULL, Indexed) — Neighborhood / Ward
- `image_url` (VARCHAR(500), NULL)
- `status` (VARCHAR(50), NOT NULL, Default: `'Submitted'`, Indexed)
- `ai_severity` (FLOAT, Default: `5.0`)
- `human_severity` (FLOAT, NULL)
- `priority_score` (FLOAT, Default: `50.0`, Indexed)
- `priority_level` (VARCHAR(20), Default: `'Medium'`, Indexed)
- `is_duplicate` (BOOLEAN, Default: `False`, Indexed)
- `canonical_report_id` (VARCHAR(36), FK -> `reports.id`, NULL)
- `resolution_notes` (TEXT, NULL)
- `resolution_image_url` (VARCHAR(500), NULL)
- `resolved_at` (TIMESTAMP WITH TIME ZONE, NULL)
- `created_at` (TIMESTAMP WITH TIME ZONE, Default: `utcnow`, Indexed)
- `updated_at` (TIMESTAMP WITH TIME ZONE, Default: `utcnow`)

### 2.6 `ai_predictions`
Computer vision inference output and explainable feature diagnostics.
- `id` (VARCHAR(36), PK, UUIDv4)
- `report_id` (VARCHAR(36), FK -> `reports.id`, UNIQUE, NOT NULL, OnDelete: CASCADE)
- `model_name` (VARCHAR(100), NOT NULL)
- `model_version` (VARCHAR(50), NOT NULL)
- `predicted_category_code` (VARCHAR(50), NOT NULL)
- `confidence` (FLOAT, NOT NULL)
- `raw_predictions` (JSON, NOT NULL) — Multi-class probability distribution dictionary
- `detected_features` (JSON, NOT NULL) — Edge density, dark pixel ratio, luminance std, saturation
- `needs_human_verification` (BOOLEAN, Default: `False`)
- `created_at` (TIMESTAMP WITH TIME ZONE, Default: `utcnow`)

### 2.7 `priority_scores`
Explainable factor components and rationale.
- `id` (VARCHAR(36), PK, UUIDv4)
- `report_id` (VARCHAR(36), FK -> `reports.id`, UNIQUE, NOT NULL, OnDelete: CASCADE)
- `composite_score` (FLOAT, NOT NULL)
- `severity_component` (FLOAT, NOT NULL)
- `safety_component` (FLOAT, NOT NULL)
- `location_risk_component` (FLOAT, NOT NULL)
- `community_impact_component` (FLOAT, NOT NULL)
- `age_component` (FLOAT, NOT NULL)
- `reasons` (JSON, NOT NULL) — String list of weight triggers
- `calculated_at` (TIMESTAMP WITH TIME ZONE, Default: `utcnow`)

### 2.8 `duplicate_candidates`
Geospatial matching links between related citizen complaints.
- `id` (VARCHAR(36), PK, UUIDv4)
- `source_report_id` (VARCHAR(36), FK -> `reports.id`, NOT NULL, OnDelete: CASCADE)
- `target_report_id` (VARCHAR(36), FK -> `reports.id`, NOT NULL, OnDelete: CASCADE)
- `distance_meters` (FLOAT, NOT NULL)
- `category_match` (BOOLEAN, NOT NULL)
- `time_diff_hours` (FLOAT, NOT NULL)
- `visual_similarity` (FLOAT, NULL)
- `composite_score` (FLOAT, NOT NULL)
- `status` (VARCHAR(50), Default: `'suggested'`) — Values: `'suggested'`, `'confirmed'`, `'rejected'`
- `notes` (TEXT, NULL)

### 2.9 `audit_logs`
Immutable record of all operational status changes, AI overrides, and dispatches.
- `id` (VARCHAR(36), PK, UUIDv4)
- `report_id` (VARCHAR(36), FK -> `reports.id`, NOT NULL, OnDelete: CASCADE)
- `user_id` (VARCHAR(36), FK -> `users.id`, NULL)
- `action` (VARCHAR(100), NOT NULL)
- `previous_state` (VARCHAR(100), NULL)
- `new_state` (VARCHAR(100), NULL)
- `notes` (TEXT, NULL)
- `created_at` (TIMESTAMP WITH TIME ZONE, Default: `utcnow`)

---

## 3. Indexing & Optimization Strategy

1. **B-Tree Composite Indices**:
   - `idx_reports_status_priority`: Speeds up admin dashboard queries filtering by `(status, priority_score)`.
   - `idx_reports_created_area`: Accelerates 14-day trend charts grouped by ward.
2. **Spatial Coordinate Indices**:
   - In SQLite, bounding box queries use `(latitude, longitude)` indices.
   - In PostgreSQL, PostGIS geometry points use `GIST (ST_SetSRID(ST_MakePoint(longitude, latitude), 4326))`.
3. **Foreign Key Integrity**:
   - Relational cascades ensure that deleting or archiving a demo report cleanly cascades across child AI predictions, priority breakdowns, assignments, and audit logs without orphan records.
