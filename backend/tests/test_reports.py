def test_get_categories(client):
    res = client.get("/api/reports/categories")
    assert res.status_code == 200
    categories = res.json()
    assert len(categories) >= 8
    codes = [c["code"] for c in categories]
    assert "pothole" in codes
    assert "road_damage" in codes
    assert "garbage_overflow" in codes

def test_submit_report_and_ai_processing(client, citizen_token):
    # Submit report with coordinates and description
    payload = {
        "title": "Severe pothole near Koramangala 80ft Road",
        "description": "Massive deep hole in the middle of the road causing dangerous traffic swerving and motorcycle accidents.",
        "category_code": "pothole",
        "latitude": 12.9344,
        "longitude": 77.6256,
        "address": "Near 80ft Road Junction, Koramangala",
        "area": "Koramangala"
    }
    res = client.post(
        "/api/reports",
        data=payload,
        headers={"Authorization": f"Bearer {citizen_token}"}
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["tracking_number"].startswith("CP-")
    assert data["status"] == "Submitted"
    assert data["priority_level"] in ["Medium", "High", "Critical"]
    assert data["ai_severity"] >= 5
    assert data["ai_prediction"] is not None
    assert data["ai_prediction"]["predicted_category_code"] == "pothole"
    assert data["ai_prediction"]["confidence"] >= 0.25
    assert len(data["priority_breakdown"]["reasons"]) > 0

def test_get_my_reports(client, citizen_token):
    res = client.get("/api/reports/my", headers={"Authorization": f"Bearer {citizen_token}"})
    assert res.status_code == 200
    reports = res.json()
    assert isinstance(reports, list)
    assert len(reports) > 0
