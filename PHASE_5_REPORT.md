# CivicPulse AI — Phase 5 Engineering Report: Website & UX Modernization

**Date**: November 2026  
**Branch**: `phase-5-website-ux`  
**Git Tag**: `v0.5`  
**Authors**: Senior Full-Stack & UI/UX Engineering Team  

---

## 1. Executive Summary

Phase 5 delivers a complete, accessible, mobile-first frontend experience and municipal operations console. It eliminates the traditional disconnect between citizen submission and municipal dispatch through intelligent pre-submission duplicate prevention, transparent tracking, and automated resolution verification audits.

Key accomplishments:
1. **Mobile-First Citizen Reporting**: Added real GPS capture with accuracy circle, camera capture (`capture="environment"`), and authoritative citizen category selection.
2. **Pre-Submission Duplicate Warning Modal**: Spatial scan detects nearby issues within category radius; citizens can view the closest report and click `[View & Upvote]` to escalate community priority instead of filing redundant duplicates.
3. **Public Status Tracking Without Login**: Direct tracking code lookup on the Landing Page and an interactive 5-stage progression timeline on the Issue Dossier with human verification notes ("Under review by BBMP Ward 150 engineer").
4. **Priority v2 Triage Queue**: Multi-select issue ledger sorted by Priority v2 with bulk status change and department dispatch actions.
5. **Resolution Verification Audit Queue**: Supervisor audit view displaying before and after photos side-by-side with OpenCLIP scene consistency score, defect disappearance status, and `[Confirm Resolution]` / `[Reject & Reopen]` action buttons.
6. **OpenStreetMap Chronic Recurrence Corridors**: Dedicated panel and GIS map overlay displaying corridors with $\ge 3$ incidents in 90 days with civil engineering root-cause advisory recommendations.
7. **GIS Map Modernization**: Cluster toggle between HDBSCAN Dynamic Clusters, DBSCAN Provisional Clusters (eps=300m), and Individual Markers, alongside a persistent synthetic demo data disclaimer banner.
8. **Accessibility & Build**: WCAG AA color contrast, full ARIA labelling, clean frontend Vite build in 2.25s, and 58 passing backend tests.

---

## 2. Technical Implementation Details

### 2.1 Citizen Reporting Flow (`ReportIssuePage.tsx`)
- **Native Camera Capture**: Supported via `<input type="file" accept="image/*" capture="environment" />` with dedicated "Take Photo (Camera)" button alongside file upload.
- **Real GPS Capture with Accuracy Circle**: Reads `pos.coords.accuracy` via `navigator.geolocation.getCurrentPosition(..., { enableHighAccuracy: true })` and renders a semi-transparent accuracy buffer circle on Leaflet map.
- **Authoritative Category Selection Policy**: Clear visual banner clarifying that the citizen's category choice is authoritative; AI models provide suggestions without auto-overriding.
- **Pre-Submission Duplicate Warning**:
  - Automatically queries `POST /api/reports/check-duplicate` before submission.
  - If candidates are detected within the category-specific radius + GPS margin, displays the closest report's thumbnail, title, distance (e.g. `12m away`), time gap, and status.
  - Citizens can choose:
    - `[View & Upvote]`: Calls `POST /api/reports/{id}/upvote`, increments community count, elevates priority, and navigates to the existing dossier.
    - `[Report Anyway]`: Bypasses the modal and submits a distinct report.

### 2.2 Public Issue Status Tracking (`LandingPage.tsx` & `IssueDetailsPage.tsx`)
- **No-Auth Status Lookup**: Citizens can enter a tracking number (e.g. `CP-2026-0001`) on the Landing Page search card to query `GET /api/reports/track/{tracking_number}`.
- **Visual Progression Timeline**: Renders 5 milestone stages:
  1. `Submitted` (Logged & queued)
  2. `Under Review` (Desk assessment by ward engineers)
  3. `Verified` (AI & supervisor validated)
  4. `In Progress` (Dispatched to BBMP/BWSSB/BESCOM work crew)
  5. `Resolved` (Photographic evidence verified)
- **Human Verification Notes**: Prominently displays the responsible municipal department and engineer review status.

### 2.3 Municipal Triage & Bulk Operations (`IssueManagementPage.tsx`)
- **Priority v2 Queue**: Sorted by default on `priority_score desc` with interactive column sorting and multi-field filters (category, ward, status, priority, text search).
- **Bulk Operations**: Multi-select checkboxes enable batch status changes (e.g. transitioning multiple tickets to `Under Review` or `In Progress`) and bulk department dispatches via `POST /api/admin/reports/bulk-action`.

### 2.4 Resolution Verification Audit Queue (`IssueManagementPage.tsx` Tab 2)
- Inspects resolved tickets via `GET /api/admin/resolution-audit`.
- Displays side-by-side photographic evidence: citizen before-photo and contractor completion after-photo.
- Displays AI verification metrics: composite score, OpenCLIP ViT-B/32 scene background consistency ($\ge 55\%$), and defect disappearance flag.
- Enables supervisor decisions:
  - `Confirm Resolution`: Confirms closure and marks verification as `verified`.
  - `Reject & Reopen`: Transitions ticket back to `In Progress` for remedial work with mandatory audit notes.

### 2.5 OpenStreetMap Chronic Failure Corridors (`IssueManagementPage.tsx` Tab 3 & `MapPage.tsx`)
- Evaluates road segments with $\ge 3$ reports in 90 days (`GET /api/map/recurring-corridors`).
- Renders colored polyline vectors on Leaflet GIS map with interactive popups containing incident counts and civil engineering root-cause advisory recommendations.

### 2.6 GIS Map Modernization (`MapPage.tsx`)
- **Persistent Evaluation Banner**: Prominently states: *"Synthetic Demo Data: Seeded records for municipal decision-support evaluation and algorithmic stress-testing."*
- **Cluster Mode Toggle**: Switch between HDBSCAN Dynamic Clusters (spherical radians), DBSCAN Provisional Clusters (eps=300m), and Individual Markers Only.
- **Split View**: Synchronized list view allowing users to click and pan directly to mapped tickets.

---

## 3. Files Created or Modified

| Path | Action | Description |
| :--- | :--- | :--- |
| `backend/alembic/versions/006_add_upvote_count_to_reports.py` | Created | Alembic migration adding `upvote_count` column to `reports` |
| `backend/app/models/__init__.py` | Modified | Added `upvote_count` attribute to `Report` model |
| `backend/app/schemas/__init__.py` | Modified | Added `upvote_count`, resolution verification fields to schemas |
| `backend/app/services/duplicate_service.py` | Modified | Added `find_presubmission_duplicates` spatial query method |
| `backend/app/api/routes/reports.py` | Modified | Added `track_report_by_number`, `check-duplicate`, `upvote` routes |
| `backend/app/api/routes/admin.py` | Modified | Added bulk action, resolution audit queue, and audit decision routes |
| `frontend/src/types/index.ts` | Modified | Added types for duplicate candidates, audit items, corridors, dispatch route |
| `frontend/src/services/api.ts` | Modified | Added client methods for all Phase 5 citizen and admin endpoints |
| `frontend/src/pages/ReportIssuePage.tsx` | Modified | Camera support, GPS accuracy circle, duplicate warning modal, upvote flow |
| `frontend/src/pages/LandingPage.tsx` | Modified | Added public tracking code search card with error handling |
| `frontend/src/pages/IssueDetailsPage.tsx` | Modified | Added 5-stage status progression timeline and human verification notes |
| `frontend/src/pages/IssueManagementPage.tsx` | Modified | Added Triage Queue with bulk actions, Resolution Audit Queue, and Corridors panel |
| `frontend/src/pages/MapPage.tsx` | Modified | Added cluster mode toggle, chronic corridors layer, and synthetic demo banner |
| `frontend/src/components/maps/LeafletMap.tsx` | Modified | Supported GPS accuracy circle and chronic corridor polyline overlays |
| `backend/tests/test_website_ux.py` | Created | 5 automated tests for public tracking, duplicate check, upvote, bulk actions, audit |

---

## 4. Test & Build Execution Results

### 4.1 Unit Test Execution Output
```
backend/tests/test_website_ux.py::test_public_tracking_without_login PASSED [ 20%]
backend/tests/test_website_ux.py::test_presubmission_duplicate_scanner PASSED [ 40%]
backend/tests/test_website_ux.py::test_report_upvote_and_community_escalation PASSED [ 60%]
backend/tests/test_website_ux.py::test_admin_bulk_actions PASSED         [ 80%]
backend/tests/test_website_ux.py::test_admin_resolution_verification_audit PASSED [100%]
============================== 5 passed in 1.06s ==============================
```

### 4.2 Full Backend Test Suite
```
58 passed, 1 skipped in 261.25s (0:04:21)
```

### 4.3 Frontend Production Build
```
vite v8.3.8 building client environment for production...
transforming...
✓ 2551 modules transformed.
rendering chunks...
dist/index.html                                1.10 kB │ gzip:   0.59 kB
dist/assets/index-DsHongp3.css                54.89 kB │ gzip:   9.77 kB
dist/assets/ReportIssuePage-jbTcSwqx.js       18.40 kB │ gzip:   5.60 kB
dist/assets/IssueManagementPage-CsAxIvxp.js   28.69 kB │ gzip:   6.83 kB
dist/assets/IssueDetailsPage-Bo15-oYT.js      29.80 kB │ gzip:   7.47 kB
dist/assets/LeafletMap-dwhCYsuD.js           156.03 kB │ gzip:  46.01 kB
dist/assets/index-Cq_CVL7J.js                240.57 kB │ gzip:  74.96 kB
dist/assets/AdminDashboard-C32NsoXE.js       485.00 kB │ gzip: 135.33 kB
✓ built in 2.25s
```

---

## 5. Deferred Items & User Action
1. **Real Field Photos for Resolution Calibration**: Supervisor audits are fully functional; field calibration of the $0.55$ scene similarity threshold on real before/after photographs remains a user action item.
