# Data Card — CivicPulse AI Datasets & Spatial Provenance

## 1. Dataset Overview

CivicPulse AI utilizes three primary data categories:
1. **Synthetic Demo Civic Reports**: Procedurally generated baseline data representing citizen grievance tickets across municipal Bengaluru (BBMP wards).
2. **OpenStreetMap Spatial Features**: Road network geometries and critical Point-of-Interest (POI) locations.
3. **Out-of-Distribution (OOD) Evaluation Set**: Real-world civic issue photographs used as a qualitative smoke test for vision triage.

---

## 2. Synthetic Citizen Reports Dataset

### 2.1 Provenance & Purpose
- **Generation Method**: Synthesized using deterministic seeding scripts (`backend/app/database/seed_data.py`).
- **Database Tagging**: Every synthetic record contains `is_synthetic = True` as a non-nullable Boolean column, enforcing strict transparency across database queries, user interface views, and CSV exports.
- **Volume**: 30 initial municipal reports seeded across central Bengaluru (Koramangala, Indiranagar, MG Road, Whitefield).
- **Attributes Captured**:
  - Unique tracking identifiers (`CP-YYYY-XXXX`)
  - Issue categories (Pothole, Road Damage, Garbage Overflow, Illegal Dumping, Water Leakage, Blocked Drain, Broken Streetlight, Damaged Infrastructure)
  - Coordinates (WGS84 decimal degrees constrained to Bengaluru urban bounds: Lat $[12.85, 13.10]$, Lon $[77.45, 77.75]$)
  - Status lifecycle stages (`Submitted`, `Under Review`, `Verified`, `Assigned`, `In Progress`, `Resolved`, `Rejected`)
  - Physical severity (1–10) and multi-factor priority scores (0–100)

### 2.2 Ethical Transparency
- **No Citizen PII**: Synthetic records contain fictional citizen identifiers, non-operational contact handles, and synthetic geographic points.
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

- **Volume**: 20 curated photographs illustrating real municipal infrastructure issues.
- **Annotations**: `labels.csv` mapping filenames to ground-truth category codes and difficulty descriptors.
- **Classification Role**: Smoke test fixture for verifying classifier execution, confidence extraction, and abstention behavior.
- **Evaluation Disclaimer**: Due to small sample size ($N=20$), this set serves as an architectural integration check rather than statistically significant benchmark evidence. Real model validation requires large-scale field test collections.
