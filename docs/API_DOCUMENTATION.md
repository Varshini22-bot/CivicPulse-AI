# CivicPulse AI — RESTful API Documentation

## 1. Authentication & Base URL
- **Base URL**: `http://127.0.0.1:8000/api`
- **Interactive Documentation**: `http://127.0.0.1:8000/docs` (Swagger UI) / `http://127.0.0.1:8000/redoc` (ReDoc)
- **Authentication**: Bearer Token in `Authorization` header (`Authorization: Bearer <jwt_token>`).

---

## 2. Authentication Endpoints (`/api/auth`)

### 2.1 Citizen Registration
- **`POST /api/auth/register`**
- **Public**: Yes
- **Request Body**:
  ```json
  {
    "email": "citizen@example.com",
    "password": "SecurePassword123!",
    "full_name": "Arjun Patel",
    "phone": "+91-98800-11223"
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "id": "uuid-string",
    "email": "citizen@example.com",
    "full_name": "Arjun Patel",
    "role": "citizen",
    "is_active": true,
    "phone": "+91-98800-11223"
  }
  ```

### 2.2 User Login
- **`POST /api/auth/login`**
- **Public**: Yes
- **Request Body**:
  ```json
  {
    "email": "officer@civicpulse.org",
    "password": "admin"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5...",
    "token_type": "bearer",
    "user": {
      "id": "uuid-string",
      "email": "officer@civicpulse.org",
      "full_name": "Chief Engineer Ramesh Rao",
      "role": "admin"
    }
  }
  ```

### 2.3 Current User Profile
- **`GET /api/auth/me`**
- **Requires Auth**: Yes (Bearer Token)
- **Response** (`200 OK`): User object.

---

## 3. Citizen Report Endpoints (`/api/reports`)

### 3.1 Fetch Categories
- **`GET /api/reports/categories`**
- **Public**: Yes
- **Response** (`200 OK`): Array of 8 supported categories (`id`, `name`, `code`, `description`, `icon`, `base_severity_weight`).

### 3.2 Submit Civic Report
- **`POST /api/reports`**
- **Public / Optional Auth**: If logged in, links to citizen account; otherwise accepted as guest.
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `title` (str, 5–255 chars)
  - `description` (str, min 10 chars)
  - `category_code` (str, e.g. `pothole`, `garbage_overflow`, `water_leakage`)
  - `latitude` (float, e.g. `12.9716`)
  - `longitude` (float, e.g. `77.5946`)
  - `address` (optional str)
  - `area` (optional str, e.g. `Indiranagar`)
  - `image` (optional file, max 10MB, JPG/PNG/WEBP)
- **Response** (`201 Created`): Complete `ReportDetailOut` including AI diagnostics, 5-factor priority score, and duplicate candidate links.

### 3.3 List Citizen's Own Reports
- **`GET /api/reports/my`**
- **Requires Auth**: Yes (`citizen` or `admin`)
- **Response** (`200 OK`): Array of submitted issues for current user.

### 3.4 Issue Detail View
- **`GET /api/reports/{id}`**
- **Public**: Yes
- **Response** (`200 OK`): Comprehensive dossier including tracking number, priority breakdown, assignments, duplicate candidate links, and audit history.

### 3.5 Withdraw Report
- **`POST /api/reports/{id}/withdraw`**
- **Requires Auth**: Yes (Must be the reporting citizen or an admin)
- **Response** (`200 OK`): Report updated with status `Withdrawn`.

---

## 4. Municipal Operations & Administration (`/api/admin`)

*All `/api/admin` endpoints strictly require an active user with role `admin`.*

### 4.1 Search & Filter Issue Ledger
- **`GET /api/admin/reports`**
- **Query Parameters**:
  - `status`: Filter by status (`Submitted`, `Under Review`, `Verified`, `Assigned`, `In Progress`, `Resolved`, `Rejected`, `Withdrawn`)
  - `priority`: Filter by priority level (`Critical`, `High`, `Medium`, `Low`)
  - `category_id`: UUID of category
  - `area`: Ward / neighborhood name
  - `search`: Full-text search across tracking number, title, description, and address
  - `sort_by`: Column to sort on (default `created_at` or `priority_score`)
  - `sort_dir`: `asc` or `desc`
  - `page`: Page number (default `1`)
  - `limit`: Items per page (default `20`, max `100`)
- **Response** (`200 OK`): Paginated envelope (`items`, `total`, `page`, `limit`, `total_pages`).

### 4.2 Status Transition
- **`PATCH /api/admin/reports/{id}/status`**
- **Request Body**:
  ```json
  {
    "status": "In Progress",
    "notes": "Emergency pothole repair crew dispatched with asphalt compactor.",
    "resolution_image_url": null
  }
  ```
- **Response** (`200 OK`): Updated report with audit entry appended.

### 4.3 Human AI Override
- **`POST /api/admin/reports/{id}/override`**
- **Request Body**:
  ```json
  {
    "verified_category_code": "pothole",
    "human_severity": 8,
    "notes": "On-site inspector confirmed road depression exceeds automated visual depth estimate."
  }
  ```
- **Response** (`200 OK`): Recalculated priority score, adjusted severity, and audit trail.

### 4.4 Departmental Dispatch
- **`POST /api/admin/reports/{id}/assign`**
- **Request Body**:
  ```json
  {
    "department_id": "dept-uuid",
    "staff_id": "staff-uuid",
    "notes": "Assigned to Ward 112 rapid remediation unit."
  }
  ```

### 4.5 Reset Demo Dataset
- **`POST /api/admin/reset-demo-data`**
- **Response** (`200 OK`): Re-seeds 140+ realistic Bengaluru test civic reports and duplicate clusters.

---

## 5. Geospatial & Maps (`/api/map`)

### 5.1 GeoJSON Issue Markers
- **`GET /api/map/markers`**
- **Query Parameters**: `category_id`, `priority`, `status`, `area`
- **Response** (`200 OK`): Standard GeoJSON FeatureCollection or marker array with coordinates and priority color codes.

### 5.2 Hotspot Cluster Detection
- **`GET /api/map/hotspots`**
- **Query Parameters**: `eps_meters` (default 800m), `min_samples` (default 3)
- **Response** (`200 OK`): Array of geographic density clusters detected via DBSCAN.

### 5.3 Radius Proximity Query
- **`GET /api/map/nearby`**
- **Query Parameters**: `latitude`, `longitude`, `radius_meters` (default 1000m)
- **Response** (`200 OK`): Reports within radius sorted by ascending distance.

---

## 6. Analytics & CSV Export (`/api/analytics`)

### 6.1 Operational KPIs
- **`GET /api/analytics/kpis`**
- Returns total reports, open issues, critical issues, average priority, resolution rate %, and avg resolution time.

### 6.2 Time-Series & Distribution Charts
- **`GET /api/analytics/charts`**
- Returns category distributions, priority breakdowns, status distributions, 14-day submission trends, and area hotspots.

### 6.3 Standardized CSV Export
- **`GET /api/analytics/export`**
- Generates downloadable `Content-Type: text/csv` file with RFC 4180 compliant quoting.
