import uuid
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models import User, Report, Category, Department
from app.core.security import create_access_token
from app.services.report_service import ReportService


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def admin_headers(admin_token: str):
    return {"Authorization": f"Bearer {admin_token}"}


def test_public_tracking_without_login(test_client: TestClient, db_session: Session):
    """Citizens can track status by tracking code without authentication."""
    cat = db_session.query(Category).first()
    tracking_no = f"CP-TRACK-{uuid.uuid4().hex[:6].upper()}"
    report = Report(
        tracking_number=tracking_no,
        title="Tracking Test Pothole",
        description="Public tracking verification description",
        latitude=12.9344,
        longitude=77.6256,
        category_id=cat.id,
        status="Under Review"
    )
    db_session.add(report)
    db_session.commit()

    # Query public tracking route without Authorization header
    resp = test_client.get(f"/api/reports/track/{tracking_no}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tracking_number"] == tracking_no
    assert data["status"] == "Under Review"
    assert "audit_history" in data

    # Verify privacy redaction on public endpoint
    assert data["latitude"] is None
    assert data["longitude"] is None
    assert data["address"] is None
    assert "citizen_id" not in data

    # Negative test: Non-existent tracking number
    resp_404 = test_client.get("/api/reports/track/CP-INVALID-99999")
    assert resp_404.status_code == 404


def test_public_tracking_code_high_entropy_and_unguessable(db_session: Session):
    """Generated tracking codes must be cryptographically unguessable (>40 bits entropy)."""
    codes = set()
    for _ in range(50):
        code = ReportService.generate_tracking_number(db_session)
        assert code.startswith(f"CP-{datetime.now().year}-")
        suffix = code.split("-")[-1]
        assert len(suffix) >= 8
        # Ensure unambiguous character set
        for ch in suffix:
            assert ch in "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
        codes.add(code)
    # Zero collisions among 50 generated samples
    assert len(codes) == 50


def test_public_tracking_rate_limiting(test_client: TestClient):
    """Public tracking endpoint must enforce rate limiting (SlowAPI 20/minute)."""
    # Send 25 consecutive rapid requests
    responses = [test_client.get("/api/reports/track/CP-RATE-LIMIT-TEST") for _ in range(25)]
    status_codes = [r.status_code for r in responses]
    # At least one request beyond the limit must receive 429 Too Many Requests
    assert 429 in status_codes


def test_presubmission_duplicate_scanner(test_client: TestClient, db_session: Session):
    """Pre-submission spatial query identifies nearby reports within category radius."""
    import random
    cat = db_session.query(Category).filter(Category.code == "pothole").first()
    if not cat:
        cat = db_session.query(Category).first()

    # Choose a unique coordinate area away from existing fixtures to isolate the test report
    unique_lat = round(12.10000 + random.uniform(0.01, 0.40), 5)
    unique_lon = round(77.10000 + random.uniform(0.01, 0.40), 5)
    report = Report(
        tracking_number=f"CP-NEAR-{uuid.uuid4().hex[:6].upper()}",
        title="Nearby Road Pothole",
        description="Existing pothole report for pre-submission test",
        latitude=unique_lat,
        longitude=unique_lon,
        category_id=cat.id,
        status="Submitted"
    )
    db_session.add(report)
    db_session.commit()

    # Query duplicate check 10 meters away
    resp = test_client.post("/api/reports/check-duplicate", json={
        "category_code": cat.code,
        "latitude": unique_lat + 0.00008,
        "longitude": unique_lon + 0.00004
    })
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)
    matching = [r for r in results if r["tracking_number"] == report.tracking_number]
    assert len(matching) > 0
    assert matching[0]["distance_meters"] < 25.0
    assert "upvote_count" in matching[0]


def test_report_upvote_and_community_escalation(test_client: TestClient, db_session: Session):
    """Upvoting an existing report increases community count and elevates priority score."""
    cat = db_session.query(Category).first()
    report = Report(
        tracking_number=f"CP-UPVOTE-{uuid.uuid4().hex[:6].upper()}",
        title="Community Upvote Test",
        description="Community escalation test issue description",
        latitude=12.9350,
        longitude=77.6250,
        category_id=cat.id,
        status="Submitted",
        upvote_count=1,
        priority_score=40.0
    )
    db_session.add(report)
    db_session.commit()

    resp = test_client.post(f"/api/reports/{report.id}/upvote")
    assert resp.status_code == 200
    data = resp.json()
    assert data["upvote_count"] == 2
    assert data["priority_score"] >= 40.0


def test_admin_bulk_actions(test_client: TestClient, admin_headers: dict, db_session: Session):
    """Admin can execute bulk status changes across multiple tickets."""
    cat = db_session.query(Category).first()
    r1 = Report(
        tracking_number=f"CP-BULK1-{uuid.uuid4().hex[:6].upper()}",
        title="Bulk Test 1",
        description="Description for bulk test 1",
        latitude=12.9716,
        longitude=77.5946,
        category_id=cat.id,
        status="Submitted"
    )
    r2 = Report(
        tracking_number=f"CP-BULK2-{uuid.uuid4().hex[:6].upper()}",
        title="Bulk Test 2",
        description="Description for bulk test 2",
        latitude=12.9717,
        longitude=77.5947,
        category_id=cat.id,
        status="Submitted"
    )
    db_session.add_all([r1, r2])
    db_session.commit()

    # Bulk status transition to Under Review
    resp = test_client.post("/api/admin/reports/bulk-action", headers=admin_headers, json={
        "report_ids": [r1.id, r2.id],
        "action": "change_status",
        "status": "Under Review",
        "notes": "Bulk supervisor triage to Under Review"
    })
    assert resp.status_code == 200
    assert resp.json()["affected_count"] == 2

    # Refresh from DB
    db_session.refresh(r1)
    db_session.refresh(r2)
    assert r1.status == "Under Review"
    assert r2.status == "Under Review"


def test_admin_resolution_verification_audit(test_client: TestClient, admin_headers: dict, db_session: Session):
    """Supervisor can list and audit resolution verification submissions."""
    cat = db_session.query(Category).first()
    r = Report(
        tracking_number=f"CP-AUDIT-{uuid.uuid4().hex[:6].upper()}",
        title="Resolution Audit Test",
        description="Resolved issue pending supervisor confirmation",
        latitude=12.9716,
        longitude=77.5946,
        category_id=cat.id,
        status="Resolved",
        resolution_verification_status="flagged_for_review",
        resolution_verification_details={
            "verification_score": 0.58,
            "scene_consistency": 0.52,
            "defect_disappeared": True,
            "reasons": ["Visual scene divergence"]
        }
    )
    db_session.add(r)
    db_session.commit()

    # 1. Fetch audit queue
    resp = test_client.get("/api/admin/resolution-audit", headers=admin_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert any(item["id"] == r.id for item in items)

    # 2. Supervisor decides to reject and reopen work order
    resp_reject = test_client.post(
        f"/api/admin/reports/{r.id}/audit-resolution",
        headers=admin_headers,
        json={"decision": "reject_reopen", "notes": "Insufficient photographic proof"}
    )
    assert resp_reject.status_code == 200
    assert resp_reject.json()["status"] == "In Progress"
    assert resp_reject.json()["resolution_verification_status"] == "audit_rejected"

    # 3. Supervisor decides to confirm resolution
    resp_confirm = test_client.post(
        f"/api/admin/reports/{r.id}/audit-resolution",
        headers=admin_headers,
        json={"decision": "confirm", "notes": "Supervisor manually verified site repair"}
    )
    assert resp_confirm.status_code == 200
    assert resp_confirm.json()["resolution_verification_status"] == "verified"
