# CivicPulse AI — User & Operator Guide

## 1. Quick Start & Default Credentials

CivicPulse AI comes preloaded with two primary user personas for immediate evaluation:

| Persona | Email | Password | Role | Permissions |
|---|---|---|---|---|
| **Municipal Officer** | `officer@civicpulse.org` | `admin` | `admin` | Full operational control, AI overrides, dispatch, analytics, exports |
| **Citizen Reporter** | `arjun.patel@example.com` | `citizen` | `citizen` | Submit reports, track live grievance triage, view priority scores |

---

## 2. Citizen Experience Walkthrough

### 2.1 Submitting a Civic Issue
1. Click **"Report Issue"** in the top navigation bar or home landing page.
2. **Defect Details**:
   - Provide a clear, concise title (e.g., *"Dangerous asphalt pothole near 12th Main cross"*).
   - Select the matching civic category from the 8 options (Pothole, Road Damage, Garbage Overflow, Illegal Dumping, Water Leakage, Blocked Drain, Broken Streetlight, Damaged Infrastructure).
   - Enter an observational description of the defect and safety risk.
3. **Location Specification**:
   - Enter street address or landmark (e.g., *"100ft Road, Indiranagar"*).
   - Click the interactive Leaflet map to place an exact GPS pin, or use your browser's current location.
4. **Photographic Evidence**:
   - Upload an image file (JPG, PNG, or WEBP, max 10MB).
   - CivicPulse AI will automatically analyze the image for edge density and cavity depth.
5. Click **"Submit Civic Report"**.
   - You will immediately receive a unique tracking number (e.g. `CP-2026-1042`).

### 2.2 Tracking Your Reports
1. Visit **"Citizen Portal"** to view your active grievances.
2. Review the live triage badge (`Submitted`, `Under Review`, `Assigned`, `In Progress`, `Resolved`).
3. Click any report to view its full dossier, including assigned department and estimated priority score.
4. If an issue has resolved itself or was reported in error, click **"Withdraw"** to close the ticket.

---

## 3. Municipal Operations Control Center

### 3.1 Managing the Issue Ledger
1. Log in as a Municipal Officer (`officer@civicpulse.org`).
2. Navigate to **"Issue Management"** in the navigation bar.
3. Use the search bar to locate issues by tracking number, title, description, or street address.
4. Apply multi-criteria filters:
   - **Status**: Focus on `Submitted` or `Under Review` queues.
   - **Priority**: Filter by `Critical` or `High` urgency.
   - **Category**: Filter by specific civic defect types.
   - **Municipal Sector**: Filter by ward or locality (e.g., `Indiranagar`, `Whitefield`).

### 3.2 Inspecting Computer Vision & 5-Factor Priority
Click any issue in the ledger to open its comprehensive dossier:
- **Computer Vision Diagnostics**: Inspect the model's confidence rating, edge density profile, dark pixel depth ratio, and multi-class probability distribution.
- **5-Factor Priority Breakdown**: Review the weighted score breakdown across Defect Severity (35%), Public Safety (25%), Location Risk (15%), Community Impact (15%), and SLA Age (10%).

### 3.3 Human-in-the-Loop AI Overrides
If the automated vision model misclassifies an issue or underestimates severe on-site conditions:
1. Click the **"Override AI Prediction"** button.
2. Select the corrected category.
3. Adjust the severity slider (1 to 10).
4. Enter an accountable justification note (e.g. *"Field engineer confirmed deep structural fissure"*).
5. Click **"Confirm Override & Recalculate"**.
6. The composite priority score will recalculate immediately, and an immutable entry will be written to the **Municipal Audit Trail**.

### 3.4 Managing Duplicate Reports
When multiple citizens report the same defect:
1. The **Duplicate Candidates** section will display nearby reports within 100 meters.
2. Review the distance, time gap, and match percentage.
3. Click **"Confirm Merge"** to link the duplicate report to the primary canonical issue, or **"Reject"** if they represent separate issues.

### 3.5 Dispatch & Resolution Workflow
1. Click **"Update Status"** to transition the issue from `Submitted` -> `Under Review` -> `Verified` -> `Assigned` -> `In Progress`.
2. To assign to a department, select the responsible agency (BBMP, BWSSB, BESCOM) and active engineer.
3. Upon completion of field repairs, transition the status to `Resolved`, attach resolution notes, and optionally link a resolution evidence photo.

### 3.6 Interactive GIS Map & Hotspot Analysis
1. Navigate to **"Live GIS Map"**.
2. View all municipal reports rendered as color-coded pins (Red: Critical, Orange: High, Yellow: Medium, Green: Low).
3. Toggle the **"Hotspot Clusters"** layer to view geographic density circles calculated via DBSCAN, highlighting neighborhoods with concentrated infrastructure failures.

### 3.7 Analytics & CSV Exports
1. Navigate to **"Analytics"** to inspect resolution efficiency, departmental workload distributions, and 14-day defect volume trends.
2. Click **"Export CSV"** to generate an RFC 4180 compliant municipal report containing all filtered records for offline reporting.
