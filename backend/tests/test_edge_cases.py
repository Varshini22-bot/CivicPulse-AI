import io
import uuid
import pytest
from PIL import Image
from fastapi import HTTPException
from app.models import Report, Category, User
from app.services.duplicate_service import DuplicateService
from app.services.geospatial_service import GeospatialService
from app.services.routing_service import RoutingService
from app.services.recurrence_service import RecurrenceService
from app.services.resolution_verification_service import ResolutionVerificationService
from app.services.privacy_service import PrivacyService
from app.services.report_service import ReportService


def test_corrupted_image_upload_rejected(client, citizen_token):
    """Uploading corrupted non-image bytes must be rejected with 400 Bad Request."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    fake_bytes = b"NOT_A_VALID_IMAGE_RASTER_DATA_AT_ALL_CORRUPT"
    
    response = client.post(
        "/api/reports",
        data={
            "title": "Corrupted Image Test Report",
            "description": "Submitting corrupted image payload to test integrity validator.",
            "category_code": "pothole",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "area": "MG Road"
        },
        files={"image": ("corrupted.jpg", io.BytesIO(fake_bytes), "image/jpeg")},
        headers=headers
    )
    assert response.status_code == 400
    assert "image" in response.json()["detail"].lower()


def test_unsupported_image_extension_rejected(client, citizen_token):
    """Uploading unsupported file formats (e.g. .exe, .pdf, .txt) must return 400."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    payload = b"%PDF-1.4 fake pdf stream"
    
    response = client.post(
        "/api/reports",
        data={
            "title": "Unsupported File Extension Report",
            "description": "Testing rejection of disallowed document uploads as images.",
            "category_code": "pothole",
            "latitude": 12.9716,
            "longitude": 77.5946
        },
        files={"image": ("document.pdf", io.BytesIO(payload), "application/pdf")},
        headers=headers
    )
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_out_of_range_coordinates_rejected(client, citizen_token):
    """Latitude outside [-90, 90] or Longitude outside [-180, 180] must return 422."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    
    # Latitude out of bounds
    res1 = client.post(
        "/api/reports",
        data={
            "title": "Out of Range Latitude Report",
            "description": "Submitting invalid latitude beyond 90 degrees north.",
            "category_code": "pothole",
            "latitude": 999.0,
            "longitude": 77.5946
        },
        headers=headers
    )
    assert res1.status_code == 422

    # Longitude out of bounds
    res2 = client.post(
        "/api/reports",
        data={
            "title": "Out of Range Longitude Report",
            "description": "Submitting invalid longitude beyond 180 degrees east.",
            "category_code": "pothole",
            "latitude": 12.9716,
            "longitude": -500.0
        },
        headers=headers
    )
    assert res2.status_code == 422


def test_duplicate_check_out_of_range_coords(client):
    """Pre-submission duplicate scanner must reject coordinates outside valid ranges."""
    res = client.post(
        "/api/reports/check-duplicate",
        json={
            "category_code": "pothole",
            "latitude": 195.0,
            "longitude": 77.5946
        }
    )
    assert res.status_code == 422


def test_short_title_and_description_rejected(client, citizen_token):
    """Reports with titles < 5 chars or descriptions < 10 chars must fail validation."""
    headers = {"Authorization": f"Bearer {citizen_token}"}
    
    # Title too short (<5)
    res1 = client.post(
        "/api/reports",
        data={
            "title": "Poth",
            "description": "Valid length description for testing edge cases.",
            "category_code": "pothole",
            "latitude": 12.9716,
            "longitude": 77.5946
        },
        headers=headers
    )
    assert res1.status_code == 422

    # Description too short (<10)
    res2 = client.post(
        "/api/reports",
        data={
            "title": "Valid Long Title Here",
            "description": "Short",
            "category_code": "pothole",
            "latitude": 12.9716,
            "longitude": 77.5946
        },
        headers=headers
    )
    assert res2.status_code == 422


def test_geospatial_hotspots_boundary_conditions(db_session):
    """Hotspot detection with impossibly large min_samples or empty sets must return empty list."""
    # Min cluster size larger than any possible cluster
    clusters_hdb = GeospatialService.detect_hotspots(db_session, algorithm="hdbscan", min_cluster_size=99999)
    assert isinstance(clusters_hdb, list)
    assert len(clusters_hdb) == 0

    clusters_db = GeospatialService.detect_hotspots(db_session, algorithm="dbscan", min_samples=99999)
    assert isinstance(clusters_db, list)
    assert len(clusters_db) == 0


def test_routing_service_empty_and_single_stop(db_session):
    """Routing optimizer must handle 0 stops and 1 stop without exceptions."""
    # Zero reports
    empty_route = RoutingService.optimize_dispatch_route([])
    assert empty_route["total_stops"] == 0
    assert empty_route["total_distance_km"] == 0.0
    assert empty_route["optimization_algorithm"] == "none"

    # Single report
    rep = db_session.query(Report).first()
    if rep:
        single_route = RoutingService.optimize_dispatch_route([rep])
        assert single_route["total_inspections"] == 1
        assert single_route["total_stops"] >= 1
        assert len(single_route["ordered_stops"]) >= 1


def test_recurrence_service_point_to_line_zero_length():
    """Distance calculation on identical line endpoints (zero length segment) must not divide by zero."""
    dist = RecurrenceService._point_to_line_segment_distance(
        p_lat=12.9716, p_lon=77.5946,
        a_lat=12.9716, a_lon=77.5946,
        b_lat=12.9716, b_lon=77.5946
    )
    assert dist == 0.0

    # Point slightly away from zero-length segment
    dist2 = RecurrenceService._point_to_line_segment_distance(
        p_lat=12.9726, p_lon=77.5946,
        a_lat=12.9716, a_lon=77.5946,
        b_lat=12.9716, b_lon=77.5946
    )
    assert dist2 > 0.0


def test_resolution_verification_edge_cases(db_session):
    """Resolution verification must safely handle non-existent images or distant coordinates."""
    rep = db_session.query(Report).first()
    if not rep:
        pytest.skip("No reports available in test DB")

    # Both images missing/non-existent
    result = ResolutionVerificationService.verify_resolution(
        db=db_session,
        report=rep,
        resolution_image_url="uploads/non_existent_12345.jpg"
    )
    assert result["status"] == "unverifiable"
    assert result["verification_score"] == 0.0

    # Distant resolution coordinate (e.g. 500 km away)
    distant_result = ResolutionVerificationService.verify_resolution(
        db=db_session,
        report=rep,
        resolution_image_url=rep.image_url,
        resolution_latitude=rep.latitude + 5.0,  # ~550 km away
        resolution_longitude=rep.longitude
    )
    if distant_result["gps_distance_meters"] is not None:
        assert distant_result["gps_distance_meters"] > 1000.0


def test_privacy_service_nonexistent_image():
    """Privacy redaction must return graceful failure dict when file does not exist."""
    res = PrivacyService.anonymize_image("completely_bogus_path_987654.png")
    assert res["anonymized"] is False
    assert res["faces_detected"] == 0
    assert res["plates_detected"] == 0


def test_invalid_status_transition_rejected(db_session):
    """Direct invalid status jump (e.g. Submitted -> Resolved) must be rejected with 400."""
    rep = db_session.query(Report).filter(Report.status == "Submitted").first()
    if not rep:
        # Create a temporary submitted report
        cat = db_session.query(Category).first()
        rep = Report(
            tracking_number=f"CP-EDGE-{uuid.uuid4().hex[:6]}",
            title="Temporary Edge Case Report",
            description="Testing invalid status transition enforcement directly.",
            category_id=cat.id if cat else None,
            category_code=cat.code if cat else "other",
            latitude=12.9716,
            longitude=77.5946,
            status="Submitted",
            is_synthetic=True
        )
        db_session.add(rep)
        db_session.commit()
        db_session.refresh(rep)

    with pytest.raises(HTTPException) as exc_info:
        ReportService.update_status(
            db=db_session,
            report_id=rep.id,
            new_status="Resolved",
            user_id="system-test"
        )
    assert exc_info.value.status_code == 400
    assert "Invalid status transition" in exc_info.value.detail
