# Data Card — CivicPulse AI Datasets & Spatial Provenance

## 1. Dataset Overview

CivicPulse AI utilizes three primary data categories:
1. **Synthetic Demo Civic Reports**: Procedurally generated baseline data representing citizen grievance tickets across municipal Bengaluru (BBMP wards).
2. **OpenStreetMap Spatial Features**: Road network geometries and critical Point-of-Interest (POI) locations.
3. **Out-of-Distribution (OOD) Evaluation Set**: Synthetic defect image fixtures used as a qualitative smoke test for vision triage.

---

## 2. Synthetic Citizen Reports Dataset

### 2.1 Provenance & Purpose
- **Generation Method**: Synthesized using deterministic seeding scripts (`backend/app/database/seed_data.py`, fixed seed `seed=42`).
- **Database Tagging**: Every synthetic record contains `is_synthetic = True` as a non-nullable Boolean column, enforcing strict transparency across database queries, user interface views, and CSV exports.
- **Volume**: **140 synthetic municipal reports** seeded across 12 Bengaluru localities (135 distinct base civic issues + 5 intentional duplicate cluster pairings).
- **Attributes Captured**:
  - Unique tracking identifiers (`CP-YYYY-XXXX`)
  - Issue categories (Pothole, Road Damage, Garbage Overflow, Illegal Dumping, Water Leakage, Blocked Drain, Broken Streetlight, Damaged Infrastructure)
  - Coordinates (WGS84 decimal degrees constrained to Bengaluru urban bounds: Lat $[12.85, 13.10]$, Lon $[77.45, 77.75]$)
  - Status lifecycle stages (`Submitted`, `Under Review`, `Verified`, `Assigned`, `In Progress`, `Resolved`, `Rejected`)
  - Physical severity (1–10) and multi-factor priority scores (0–100)

### 2.2 Two-Tier Spatial Gating: Pre-Filter vs. Category Matching Radii
- **Coarse SQL Spatial Pre-Filter ($\le 50\text{m}$ / Bounding Box)**: Applied in SQL spatial queries to retrieve candidate nearby active reports without full-table scans.
- **Fine-Grained Per-Category Duplicate Thresholds**: Once candidate reports pass the 50m pre-filter, each pair is evaluated against its category-specific physical matching threshold:
  - *Pothole*: $20\text{m} + 10\text{m}$ GPS margin = $30\text{m}$ max
  - *Road Damage*: $25\text{m} + 10\text{m}$ GPS margin = $35\text{m}$ max
  - *Garbage Overflow*: $25\text{m} + 10\text{m}$ GPS margin = $35\text{m}$ max
  - *Illegal Dumping*: $35\text{m} + 10\text{m}$ GPS margin = $45\text{m}$ max
  - *Water Leakage*: $30\text{m} + 10\text{m}$ GPS margin = $40\text{m}$ max
  - *Blocked Drain*: $25\text{m} + 10\text{m}$ GPS margin = $35\text{m}$ max
  - *Broken Streetlight*: $35\text{m} + 10\text{m}$ GPS margin = $45\text{m}$ max
  - *Damaged Infrastructure*: $25\text{m} + 10\text{m}$ GPS margin = $35\text{m}$ max
- Candidates exceeding the per-category threshold (even if within 50m) fail the duplicate gate.

### 2.3 Ethical Transparency & Storage
- **No Citizen PII**: Synthetic records contain fictional citizen identifiers, non-operational contact handles, and synthetic geographic points.
- **Image Storage & In-Place Redaction**: Uploaded photos are stored on disk in `backend/uploads/` under UUID filenames. EXIF/GPS metadata is stripped on ingestion, and detected frontal faces are overwritten in-place with Gaussian blur. The server does NOT retain or serve unredacted original photos. Missed faces and unredacted vehicle license plates (which are not implemented) remain in the stored raster.
- **No False Data Presentation**: The user interface prominently displays a warning banner: *"Synthetic demo data — for evaluation and portfolio demonstration only"* on all public and municipal dashboards.

---

## 3. OpenStreetMap (OSM) Spatial Datasets

### 3.1 Road Network (`data/osm/bengaluru_roads.json`)
- **Source**: OpenStreetMap via Overpass API queries covering arterial, secondary, and residential roads in Bengaluru.
- **License**: **Open Database License (ODbL) 1.0** (OpenStreetMap Contributors).
- **Features Captured**:
  - `osm_way_id`: Unique OSM line element identifier.
  - `name`: Gazetted street name (e.g., 80 Feet Road, 100 Feet Road, Hosur Road).
  - `highway_type`: OSM classification (`primary`, `secondary`, `tertiary`, `residential`).
  - `coordinates`: Polyline coordinate array (WGS84 Lon/Lat pairs).
  - `length_meters`: Segment length computed via geodesic great-circle distance.
- **Municipal Use**: Snapping citizen incident coordinates to road segments to discover recurring failure corridors.

### 3.2 High-Risk Facilities & POIs (`data/osm/bengaluru_pois.json`)
- **Source**: Curated from OpenStreetMap facility data.
- **License**: **Open Database License (ODbL) 1.0**.
- **Coverage**: 30 critical facilities in Bengaluru:
  - Trauma centers and major hospitals (Manipal Hospital, St. John's, Victoria Hospital, Bowring & Lady Curzon, NIMHANS).
  - Educational institutions and school zones (Bishop Cotton, National Public School, Christ University, Mount Carmel).
  - High-volume transit hubs (Majestic KSRTC, Yeshwantpur Railway Station, Kempegowda Bus Station).
- **Municipal Use**: Informs Location Risk in Priority Scoring v2 (+35% for hospital zones $\le 100\text{m}$, +30% for school/transit zones $\le 100\text{m}$).

---

## 4. Evaluation Fixtures (`data/ood_bengaluru/`)

- **Volume**: 20 synthetically generated image fixtures (procedural textures, noise patterns, and geometric defect shapes created via Pillow and NumPy). None are real citizen photographs.
- **Annotations**: `labels.csv` mapping filenames to ground-truth category codes and difficulty descriptors.
- **Classification Role**: Smoke test fixture for verifying classifier execution, confidence extraction, and abstention behavior.
- **Evaluation Disclaimer**: Due to small sample size ($N=20$) and synthetic nature, this set serves as an architectural integration smoke test rather than evidence of real-world model accuracy. Real model validation requires large-scale field test collections.
