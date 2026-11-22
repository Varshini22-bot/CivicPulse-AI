def test_admin_list_reports(client, admin_token):
    res = client.get("/api/admin/reports?limit=10", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) == 10
    assert data["total"] > 100

def test_admin_status_transitions(client, admin_token):
    # Fetch a report currently in 'Submitted'
    res = client.get("/api/admin/reports?status=Submitted&limit=1", headers={"Authorization": f"Bearer {admin_token}"})
    reports = res.json()["items"]
    assert len(reports) > 0
    report_id = reports[0]["id"]

    # 1. Valid transition: Submitted -> Under Review
    patch_res = client.patch(
        f"/api/admin/reports/{report_id}/status",
        json={"status": "Under Review", "notes": "Inspector dispatched to site."},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "Under Review"

    # 2. Invalid transition: Under Review -> Resolved directly (skipping verification) should fail
    bad_res = client.patch(
        f"/api/admin/reports/{report_id}/status",
        json={"status": "Resolved", "notes": "Premature attempt"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert bad_res.status_code == 400

def test_admin_ai_override(client, admin_token):
    # Fetch any report
    res = client.get("/api/admin/reports?limit=1", headers={"Authorization": f"Bearer {admin_token}"})
    report_id = res.json()["items"][0]["id"]

    override_res = client.post(
        f"/api/admin/reports/{report_id}/override",
        json={
            "verified_category_code": "road_damage",
            "human_severity": 9,
            "notes": "Field engineer verified that defect is deep asphalt cracking rather than superficial pothole."
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert override_res.status_code == 200
    updated = override_res.json()
    assert updated["human_severity"] == 9
    assert updated["verified_category"] == "Road Damage"
    assert updated["priority_score"] > 50

def test_geospatial_hotspots_and_markers(client):
    # Map markers
    markers_res = client.get("/api/map/reports")
    assert markers_res.status_code == 200
    markers = markers_res.json()
    assert len(markers) > 50
    assert "latitude" in markers[0]
    assert "color" in markers[0]

    # Hotspots
    hotspots_res = client.get("/api/map/hotspots")
    assert hotspots_res.status_code == 200
    hotspots = hotspots_res.json()
    assert len(hotspots) > 0
    assert "center_latitude" in hotspots[0]
    assert "total_reports" in hotspots[0]

def test_analytics_and_export(client, admin_token):
    # Overview KPIs
    kpi_res = client.get("/api/analytics/kpis")
    assert kpi_res.status_code == 200
    kpis = kpi_res.json()
    assert kpis["total_reports"] > 100
    assert "resolution_rate_percent" in kpis
    assert "avg_resolution_time_hours" in kpis

    # Chart aggregations
    chart_res = client.get("/api/analytics/charts")
    assert chart_res.status_code == 200
    charts = chart_res.json()
    assert len(charts["issues_by_category"]) > 0
    assert len(charts["issues_by_priority"]) == 4
    assert len(charts["timeline_trend"]) == 14

    # CSV Export - Unauthenticated must be rejected with 401
    unauth_csv = client.get("/api/analytics/export")
    assert unauth_csv.status_code == 401

    # CSV Export - Admin succeeds and includes synthetic provenance column
    csv_res = client.get("/api/analytics/export", headers={"Authorization": f"Bearer {admin_token}"})
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "Tracking Number,Title,Category" in csv_res.text
    assert "Is Synthetic" in csv_res.text
    assert "Data Provenance" in csv_res.text
