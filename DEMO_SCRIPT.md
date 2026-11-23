# CivicPulse AI — 5-Minute Live Demonstration Script

This script provides a step-by-step walkthrough for project demonstrations, portfolio presentations, and technical interviews.

---

## 🎬 Demo Overview
- **Total Duration**: ~5 Minutes
- **Personas Demonstrated**:
  1. *Citizen Persona*: Submitting an issue, checking duplicates, and tracking ticket progress.
  2. *Municipal Engineer Persona*: Triaging tickets, inspecting spatial clusters, generating dispatch routes, and auditing repair resolution proofs.

---

## Act 1: Citizen Reporting Flow (1.5 Minutes)

### Step 1: Navigate to Report Page
- **Action**: Click `Report an Issue` on the top navigation bar.
- **Talking Point**: *"The reporting interface is designed mobile-first for citizens on the road. It provides direct camera capture and GPS geolocation."*

### Step 2: Acquire Location & Select Category
- **Action**:
  - Click `Get Current Location`. Note the GPS accuracy indicator (e.g. `±8m`) and the blue accuracy circle on the Leaflet map.
  - Select Category: `Potholes & Road Damage`.
- **Talking Point**: *"Notice the banner at the top: Citizen category selection is authoritative. While our AI models will analyze the photograph and suggest classifications, the system never silently overrides the citizen's choice."*

### Step 3: Trigger Pre-Submission Spatial Duplicate Check
- **Action**: Enter description: *"Large deep pothole on 80 Feet Road near the junction."*
- **Talking Point**: *"Before submitting, CivicPulse automatically scans the local area within a category-specific radius (25 meters for potholes). If a neighbor has already reported this exact defect, a modal appears presenting the existing ticket, its photo thumbnail, and an option to 'Upvote' instead of cluttering municipal queues."*
- **Action**: Click `Submit Report`. Note the generated tracking number (e.g. `CP-2026-0031`).

---

## Act 2: Public Status Tracking Without Login (45 Seconds)

### Step 1: Open Public Tracker
- **Action**: Return to the `Home` page. Scroll to the `Track Issue Status` search box.
- **Action**: Paste the tracking code (e.g. `CP-2026-0001`) and click `Track Status`.
- **Talking Point**: *"Citizens do not need an account or password to check the status of their civic complaints. They enter the tracking code to view an interactive 5-stage timeline from submission to resolution, complete with municipal engineer verification notes."*

---

## Act 3: Municipal Control Center & Triage Queue (1 Minute)

### Step 1: Login as Municipal Admin
- **Action**: Click `Login`, enter admin credentials (`admin@civicpulse.gov.in` / `Admin@12345`), and navigate to `Admin Console`.
- **Talking Point**: *"This is the municipal command center used by BBMP engineers and ward officers. Tickets are prioritized using our Priority v2 algorithm."*

### Step 2: Priority v2 & Explainability
- **Action**: Click on a high-priority ticket in the queue.
- **Talking Point**: *"Priority v2 is a five-factor calibrated formula. Notice the explainability breakdown: Defect Severity (35%), Public Safety Hazard (25%), Location Risk with OSM POI proximity (15%), Community Upvotes (15%), and Continuous Saturating Age Escalation (10%). Old tickets smoothly gain priority over time, preventing lower-priority issues from being forgotten."*

### Step 3: Multi-Select Bulk Operations
- **Action**: Select three checkboxes in the table and use the bulk dropdown to change status to `Under Review`.
- **Talking Point**: *"Municipal officers can batch-assign departments and update workflow states in one click."*

---

## Act 4: GIS Spatial Intelligence & Logistics (1 Minute)

### Step 1: Interactive GIS Map & Clustering
- **Action**: Navigate to `City Map`.
- **Action**: Toggle between `HDBSCAN Dynamic Clusters` and `DBSCAN Provisional Clusters`.
- **Talking Point**: *"We use spherical haversine distance with angles in radians for clustering, preventing coordinate distortion. HDBSCAN identifies variable-density hotspots across Bengaluru wards to help plan resurfacing budgets."*

### Step 2: Chronic Corridors & Engineering Advisories
- **Action**: Toggle the `Chronic Corridors` layer on the map. Click on the 80 Feet Road corridor.
- **Talking Point**: *"By snapping reports to the OpenStreetMap road network, CivicPulse identifies recurring defect corridors. When multiple failures recur on the same road, the platform generates a civil engineering root-cause advisory—recommending core sampling or storm drain inspection rather than repeated temporary asphalt patching."*

### Step 3: Dispatch Route Optimization (Google OR-Tools)
- **Action**: View the `Dispatch Routes` tab in Issue Management.
- **Talking Point**: *"For field repair crews, the system solves the Traveling Salesperson Problem using Google OR-Tools, minimizing transit time and fuel consumption across open high-priority tickets."*

---

## Act 5: Resolution Verification Audit (45 Seconds)

### Step 1: Supervisor Verification Queue
- **Action**: Navigate to the `Resolution Audit` tab in Issue Management.
- **Talking Point**: *"When a repair crew marks a ticket resolved and uploads a completion photo, CivicPulse AI executes an automated audit."*

### Step 2: Before & After Evidence Comparison
- **Action**: Click on an item in the audit queue to inspect the side-by-side photo comparison.
- **Talking Point**: *"The engine checks three signals:
  1. GPS proximity within 50 meters.
  2. OpenCLIP visual embedding cosine similarity to confirm the physical scene matches.
  3. Vision detector to verify the defect is no longer visible.
  Crucially, our policy guard never auto-rejects closures; any discrepancies are flagged for a supervisor to confirm or reopen with one click."*

---

## Summary Wrap-Up
*"In summary, CivicPulse AI bridges citizen engagement, machine learning, spatial data engineering, and municipal operations into an accountable, transparent platform."*
