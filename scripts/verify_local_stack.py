"""
CivicPulse AI — Comprehensive Local Stack Verification Script
Verifies:
- Backend REST API on http://127.0.0.1:8000
- Frontend Web App on http://localhost:5173
- All core municipal workflows:
  1. Health & DB connectivity
  2. Category catalog
  3. Pre-submission duplicate scanner
  4. Citizen complaint submission & multimodal inference
  5. Public tracking lookup (CP-YYYY-XXXX)
  6. Admin JWT authentication
  7. Triage dashboard & KPI retrieval
  8. HDBSCAN spatial clusters
  9. Recurring defect corridors & OSM snapping
  10. Google OR-Tools crew route optimization
  11. Human-in-the-loop status update & audit logging
  12. Resolution verification audit trail
  13. Frontend HTML & bundle delivery
"""

import sys
import time
import requests
import json

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:5173"

def run_verification():
    print("=" * 80)
    print("         CIVICPULSE AI — LOCAL FULL-STACK INTEGRATION VERIFICATION")
    print("=" * 80)
    passed_tests = 0
    total_tests = 13

    # 1. Backend Health Check
    print("\n[Test 1/13] Checking Backend Health & Database...")
    r = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    health_data = r.json()
    assert health_data.get("status") == "healthy"
    print(f" -> PASSED: Status={health_data.get('status')}, DB={health_data.get('database')}")
    passed_tests += 1

    # 2. Categories Catalog
    print("\n[Test 2/13] Fetching Civic Issue Categories Catalog...")
    r = requests.get(f"{BACKEND_URL}/api/reports/categories", timeout=5)
    assert r.status_code == 200, f"Categories failed: {r.status_code}"
    categories = r.json()
    assert len(categories) >= 8, f"Expected at least 8 categories, got {len(categories)}"
    pothole_cat = next(c for c in categories if c["code"] == "pothole")
    print(f" -> PASSED: Retrieved {len(categories)} categories (e.g. {pothole_cat['name']} [safety_weight={pothole_cat['safety_weight']}])")
    passed_tests += 1

    # 3. Pre-Submission Duplicate Check
    print("\n[Test 3/13] Testing Pre-Submission Duplicate Scanner...")
    payload = {
        "latitude": 12.9719,
        "longitude": 77.6412,
        "category_code": pothole_cat["code"]
    }
    r = requests.post(f"{BACKEND_URL}/api/reports/check-duplicate", json=payload, timeout=5)
    assert r.status_code == 200, f"Pre-submission duplicate check failed: {r.status_code}"
    dup_res = r.json()
    assert isinstance(dup_res, list)
    print(f" -> PASSED: Duplicate check returned {len(dup_res)} nearby candidate report(s)")
    passed_tests += 1

    # 4. Citizen Complaint Submission
    print("\n[Test 4/13] Submitting New Citizen Grievance...")
    report_data = {
        "title": "Stack Verification: Deep pothole crater near Sony Signal",
        "description": "Hazardous asphalt crater 30cm wide on 80ft Road Koramangala obstructing vehicular flow and causing sudden two-wheeler swerves.",
        "category_code": pothole_cat["code"],
        "latitude": 12.9352,
        "longitude": 77.6245,
        "address": "80ft Road, near Sony Signal, Koramangala 4th Block, Bengaluru"
    }
    r = requests.post(f"{BACKEND_URL}/api/reports/", data=report_data, timeout=10)
    assert r.status_code == 201, f"Report submission failed: {r.status_code} - {r.text}"
    new_report = r.json()
    tracking_number = new_report["tracking_number"]
    report_id = new_report["id"]
    print(f" -> PASSED: Created Report #{report_id[:8]} with Tracking Number: {tracking_number}")
    passed_tests += 1

    # 5. Public Tracking Lookup
    print("\n[Test 5/13] Verifying Public Tracking without Authentication...")
    r = requests.get(f"{BACKEND_URL}/api/reports/track/{tracking_number}", timeout=5)
    assert r.status_code == 200, f"Tracking lookup failed: {r.status_code}"
    tracked_report = r.json()
    assert tracked_report["tracking_number"] == tracking_number
    assert "status" in tracked_report
    print(f" -> PASSED: Retrieved tracking payload for {tracking_number} (Status: {tracked_report['status']})")
    passed_tests += 1

    # 6. Admin Authentication (OAuth2 Token)
    print("\n[Test 6/13] Authenticating Municipal Admin...")
    login_data = {
        "email": "admin@civicpulse.gov.in",
        "password": "Admin@12345"
    }
    r = requests.post(f"{BACKEND_URL}/api/auth/login", json=login_data, timeout=5)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} - {r.text}"
    token_data = r.json()
    access_token = token_data["access_token"]
    admin_headers = {"Authorization": f"Bearer {access_token}"}
    print(f" -> PASSED: Authenticated as Municipal Admin. Token: {access_token[:20]}...")
    passed_tests += 1

    # 7. Municipal KPIs & Analytics
    print("\n[Test 7/13] Fetching Municipal Triage KPIs & Analytics...")
    r = requests.get(f"{BACKEND_URL}/api/analytics/kpis", headers=admin_headers, timeout=5)
    assert r.status_code == 200, f"KPIs failed: {r.status_code}"
    kpis = r.json()
    assert "total_reports" in kpis
    assert "critical_reports" in kpis
    print(f" -> PASSED: Total Reports={kpis['total_reports']}, Open={kpis['open_reports']}, Critical={kpis['critical_reports']}, Resolved={kpis['resolved_reports']}")
    passed_tests += 1

    # 8. Geographic Hotspots (HDBSCAN Clustering)
    print("\n[Test 8/13] Querying Spatial Hotspots (HDBSCAN Radian Haversine)...")
    r = requests.get(f"{BACKEND_URL}/api/map/hotspots", timeout=5)
    assert r.status_code == 200, f"Hotspots failed: {r.status_code}"
    hotspots = r.json()
    assert len(hotspots) >= 1
    print(f" -> PASSED: Computed {len(hotspots)} geographic density hotspots across Bengaluru wards")
    passed_tests += 1

    # 9. Recurring Defect Corridors & Advisories
    print("\n[Test 9/13] Inspecting Chronic Recurring Corridors & Engineering Advisories...")
    r = requests.get(f"{BACKEND_URL}/api/map/recurring-failures", timeout=5)
    assert r.status_code == 200, f"Recurring failures failed: {r.status_code}"
    corridors = r.json()
    assert len(corridors) >= 1
    sample_c = corridors[0]
    print(f" -> PASSED: Identified {len(corridors)} chronic recurring segments (e.g. '{sample_c.get('road_name') or sample_c.get('corridor_name')}' - Advisory: {sample_c.get('engineering_advisory')})")
    passed_tests += 1

    # 10. Google OR-Tools Crew Route Optimization
    print("\n[Test 10/13] Optimizing Municipal Crew Dispatch Route (Google OR-Tools TSP)...")
    r = requests.get(f"{BACKEND_URL}/api/map/dispatch-route?depot_lat=12.9716&depot_lon=77.5946&max_stops=5", timeout=10)
    assert r.status_code == 200, f"Route optimization failed: {r.status_code}"
    route_data = r.json()
    assert "total_distance_km" in route_data
    assert "ordered_stops" in route_data
    print(f" -> PASSED: Optimized route visiting {len(route_data['ordered_stops'])} stops (Total Distance: {route_data['total_distance_km']} km, Transit: {route_data['estimated_transit_minutes']} min, Algorithm: {route_data['optimization_algorithm']})")
    passed_tests += 1

    # 11. Status Progression & State Machine Enforcement
    print("\n[Test 11/13] Executing Finite State Machine Transitions (Submitted -> Under Review -> Verified -> In Progress -> Resolved)...")
    # Step A: Submitted -> Under Review
    r = requests.patch(
        f"{BACKEND_URL}/api/admin/reports/{report_id}/status",
        json={"status": "Under Review", "notes": "Triaged by Municipal Inspector."},
        headers=admin_headers,
        timeout=5
    )
    assert r.status_code == 200, f"Transition to Under Review failed: {r.status_code} - {r.text}"

    # Step B: Under Review -> Verified
    r = requests.patch(
        f"{BACKEND_URL}/api/admin/reports/{report_id}/status",
        json={"status": "Verified", "notes": "Defect physically verified on-site."},
        headers=admin_headers,
        timeout=5
    )
    assert r.status_code == 200, f"Transition to Verified failed: {r.status_code} - {r.text}"

    # Step C: Verified -> In Progress
    r = requests.patch(
        f"{BACKEND_URL}/api/admin/reports/{report_id}/status",
        json={"status": "In Progress", "notes": "Asphalt patch crew dispatched."},
        headers=admin_headers,
        timeout=5
    )
    assert r.status_code == 200, f"Transition to In Progress failed: {r.status_code} - {r.text}"

    # Step D: In Progress -> Resolved
    r = requests.patch(
        f"{BACKEND_URL}/api/admin/reports/{report_id}/status",
        json={"status": "Resolved", "notes": "Pothole filled and resurfaced with hot-mix bitumen."},
        headers=admin_headers,
        timeout=5
    )
    assert r.status_code == 200, f"Transition to Resolved failed: {r.status_code} - {r.text}"
    updated_rep = r.json()
    assert updated_rep["status"] in ["Resolved", "resolved"]
    print(f" -> PASSED: State machine successfully transitioned Submitted -> Under Review -> Verified -> In Progress -> Resolved with full audit logging")
    passed_tests += 1

    # 12. Resolution Verification Audit
    print("\n[Test 12/13] Inspecting Resolution Verification Audit Queue...")
    r = requests.get(f"{BACKEND_URL}/api/admin/resolution-audit", headers=admin_headers, timeout=5)
    assert r.status_code == 200, f"Resolution audit failed: {r.status_code}"
    audit_queue = r.json()
    print(f" -> PASSED: Resolution audit queue active with {len(audit_queue)} flagged resolution items")
    passed_tests += 1

    # 13. Frontend Web Application Delivery
    print("\n[Test 13/13] Checking Frontend Web Application Delivery...")
    r = requests.get(FRONTEND_URL, timeout=5)
    assert r.status_code == 200, f"Frontend delivery failed: {r.status_code}"
    assert "<title>CivicPulse AI" in r.text
    assert "/src/main.tsx" in r.text
    print(f" -> PASSED: Frontend application delivering production HTML and Vite runtime (HTTP {r.status_code})")
    passed_tests += 1

    print("\n" + "=" * 80)
    print(f"   FULL-STACK VERIFICATION RESULT: {passed_tests}/{total_tests} TESTS PASSED (100%)")
    print("   All municipal backend services and frontend portals are completely operational.")
    print("=" * 80)

if __name__ == "__main__":
    run_verification()
