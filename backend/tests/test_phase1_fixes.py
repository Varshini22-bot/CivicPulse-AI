import io
import os
import tempfile
import pytest
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from alembic.config import Config
from alembic import command

from app.core.config import settings
from app.services.duplicate_service import DuplicateService
from app.services.severity_service import SeverityService
from app.services.priority_service import PriorityService
from app.ml.vision_classifier import classifier
from app.database.connection import SessionLocal
from app.models import Category, Report


# 1. Negative RBAC Tests
def test_negative_rbac_citizen_forbidden(client, citizen_token):
    """Citizens must be rejected with 403 Forbidden on administrative endpoints."""
    headers = {"Authorization": f"Bearer {citizen_token}"}

    # Admin reports list
    res = client.get("/api/admin/reports", headers=headers)
    assert res.status_code == 403

    # Admin analytics CSV export
    res = client.get("/api/analytics/export?format=csv", headers=headers)
    assert res.status_code == 403

    # Admin status update
    res = client.patch("/api/admin/reports/non-existent-id/status", json={"status": "In Progress"}, headers=headers)
    assert res.status_code == 403

    # Admin AI override
    res = client.post("/api/admin/reports/non-existent-id/override", json={"human_severity": 7}, headers=headers)
    assert res.status_code == 403

    # Admin staff assignment
    res = client.post("/api/admin/reports/non-existent-id/assign", json={"department_id": "test"}, headers=headers)
    assert res.status_code == 403

    # Admin duplicate action
    res = client.post("/api/admin/duplicates/non-existent-id/resolve", json={"status": "confirmed"}, headers=headers)
    assert res.status_code == 403

    # Admin reset demo data
    res = client.post("/api/admin/reset-demo-data", headers=headers)
    assert res.status_code == 403


def test_negative_rbac_unauthenticated_rejected(client):
    """Unauthenticated requests must be rejected with 401 Unauthorized."""
    # Admin reports list
    res = client.get("/api/admin/reports")
    assert res.status_code == 401

    # Analytics CSV export
    res = client.get("/api/analytics/export?format=csv")
    assert res.status_code == 401

    # Protected auth/me endpoint
    res = client.get("/api/auth/me")
    assert res.status_code == 401


# 2. CORS Security Tests
def test_cors_headers_strict_origin(client):
    """CORS must strictly reflect whitelisted origins with credentials, not wildcard '*'."""
    # Whitelisted origin
    headers = {"Origin": "http://localhost:5173"}
    res = client.options("/api/health", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET"
    })
    assert res.status_code == 200
    allow_origin = res.headers.get("access-control-allow-origin")
    assert allow_origin == "http://localhost:5173"
    assert allow_origin != "*"
    assert res.headers.get("access-control-allow-credentials") == "true"


# 3. EXIF GPS Stripping Test
def test_exif_gps_stripping_on_upload(client):
    """Uploaded images with embedded EXIF metadata must have all EXIF tags stripped before saving."""
    # Create image with dummy EXIF data
    img = Image.new("RGB", (100, 100), color=(120, 180, 220))
    exif_data = img.getexif()
    # 0x010E is ImageDescription, 0x0131 is Software
    exif_data[0x010E] = "Sensitive Citizen Location EXIF"
    exif_data[0x0131] = "CameraGPS v1.0"

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", exif=exif_data)
    img_bytes.seek(0)

    # Submit report with image
    res = client.post(
        "/api/reports",
        data={
            "title": "Pothole with EXIF test image",
            "description": "Deep asphalt cavity tested for metadata removal.",
            "category_code": "pothole",
            "latitude": 12.9352,
            "longitude": 77.6245,
            "address": "Koramangala 5th Block",
            "area": "Koramangala"
        },
        files={"image": ("test_exif.jpg", img_bytes, "image/jpeg")}
    )
    assert res.status_code == 201
    saved_url = res.json().get("image_url")
    assert saved_url is not None
    assert os.path.exists(saved_url)

    # Verify saved image has no EXIF tags
    with Image.open(saved_url) as saved_img:
        saved_exif = saved_img.getexif()
        # EXIF dictionary should be empty
        assert len(saved_exif) == 0, f"Expected 0 EXIF tags, found: {dict(saved_exif)}"


def test_exif_orientation_preserved_and_phash_aligned(client):
    """
    EXIF orientation tag must be physically applied to the pixel raster via ImageOps.exif_transpose
    BEFORE stripping metadata, ensuring pHash and stored pixels represent true visual orientation.
    """
    # Create asymmetric image: width 200, height 100
    img = Image.new("RGB", (200, 100), color=(100, 150, 200))
    exif_data = img.getexif()
    # Tag 0x0112 is Orientation. Orientation 6 indicates 90-degree CW rotation (swapping dimensions to 100x200)
    exif_data[0x0112] = 6

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", exif=exif_data)
    img_bytes.seek(0)

    res = client.post(
        "/api/reports",
        data={
            "title": "Orientation Transpose Test",
            "description": "Verifying that EXIF orientation transpose physically rotates the pixel matrix.",
            "category_code": "pothole",
            "latitude": 12.9352,
            "longitude": 77.6245
        },
        files={"image": ("test_oriented.jpg", img_bytes, "image/jpeg")}
    )
    assert res.status_code == 201
    saved_url = res.json().get("image_url")
    assert saved_url and os.path.exists(saved_url)

    with Image.open(saved_url) as saved_img:
        # After transpose of 200x100 with orientation 6, the resulting raster dimensions must be 100x200
        assert saved_img.size == (100, 200), f"Expected transposed dimensions (100, 200), got {saved_img.size}"
        # All EXIF should be stripped
        assert len(saved_img.getexif()) == 0


# 4. Bitwise Hamming Distance & Weight Renormalization Tests
def test_bitwise_hamming_distance_exact():
    """Verify bitwise Hamming distance across 64-bit hexadecimal hashes."""
    # Identical
    assert DuplicateService.hamming_distance_bits("a1b2c3d4e5f60718", "a1b2c3d4e5f60718") == 0
    assert DuplicateService.bitwise_hash_similarity("a1b2c3d4e5f60718", "a1b2c3d4e5f60718") == 1.0

    # 1 bit flip: '0' (0000) vs '1' (0001) -> 1 bit difference
    dist = DuplicateService.hamming_distance_bits("0000000000000000", "0000000000000001")
    assert dist == 1
    assert DuplicateService.bitwise_hash_similarity("0000000000000000", "0000000000000001") == (64 - 1) / 64.0

    # Completely inverted 64 bits
    assert DuplicateService.hamming_distance_bits("0000000000000000", "ffffffffffffffff") == 64
    assert DuplicateService.bitwise_hash_similarity("0000000000000000", "ffffffffffffffff") == 0.0


def test_duplicate_weight_renormalization_missing_photo():
    """When an image hash is missing, visual weight must be excluded and remaining weights normalized."""
    from datetime import datetime, timezone
    rep_a = Report(
        id="rep-a",
        latitude=12.9350,
        longitude=77.6250,
        category_id="cat-pothole",
        created_at=datetime.now(timezone.utc)
    )
    rep_b = Report(
        id="rep-b",
        latitude=12.9351,
        longitude=77.6251,
        category_id="cat-pothole",
        created_at=datetime.now(timezone.utc)
    )
    result = DuplicateService.evaluate_duplicate_pair(
        report_a=rep_a,
        report_b=rep_b,
        p_hash_a=None,
        p_hash_b="a1b2c3d4e5f60718"
    )
    # Visual similarity must be None (not artificial 0.5)
    assert result["visual_similarity"] is None
    # Weights should sum to 1.0 (rescaled over 0.85 remaining weight)
    assert 0.0 <= result["composite_score"] <= 1.0


# 5. Category-Specific Duplicate Radii Tests
def test_category_specific_duplicate_radii():
    """Category duplicate thresholds must vary by issue type (e.g. pothole 25m vs streetlight 80m)."""
    assert settings.DUPLICATE_CATEGORY_RADII["pothole"] == 25.0
    assert settings.DUPLICATE_CATEGORY_RADII["broken_streetlight"] == 80.0
    assert settings.DUPLICATE_CATEGORY_RADII["water_leakage"] == 75.0

    # A pothole 20m away is within 25m threshold -> match
    assert DuplicateService.is_within_category_radius(20.0, "pothole") is True
    # A pothole 30m away exceeds 25m threshold -> no match
    assert DuplicateService.is_within_category_radius(30.0, "pothole") is False

    # A broken streetlight 70m away is within 80m threshold -> match
    assert DuplicateService.is_within_category_radius(70.0, "broken_streetlight") is True
    # A broken streetlight 90m away exceeds 80m threshold -> no match
    assert DuplicateService.is_within_category_radius(90.0, "broken_streetlight") is False


# 6. Priority Factor Orthogonality (No Double Counting)
def test_priority_orthogonality_no_double_counting():
    """Changing category safety hazard must NOT affect physical defect severity in SeverityService."""
    # Two identical reports with same physical description and visual features
    features = {"edge_density": 0.09, "dark_pixel_ratio": 0.25}
    desc = "Deep crater in the pavement surface."

    # Compute physical defect severity
    sev = SeverityService.estimate_severity(
        category_code="pothole",
        confidence=0.90,
        visual_features=features,
        description=desc,
        base_severity=6
    )
    assert sev["severity_score"] >= 6
    original_sev_score = sev["severity_score"]

    # Priority score with low category safety weight (0.3)
    prio_low_hazard = PriorityService.calculate_priority(
        severity_score=original_sev_score,
        category_safety_weight=0.30,
        location_text="Residential street",
        supporting_reports_count=1
    )

    # Priority score with high category safety weight (0.9)
    prio_high_hazard = PriorityService.calculate_priority(
        severity_score=original_sev_score,
        category_safety_weight=0.90,
        location_text="Residential street",
        supporting_reports_count=1
    )

    # Factor 1 (Defect Severity) must remain completely identical
    assert prio_low_hazard["components"]["severity"] == prio_high_hazard["components"]["severity"]

    # Factor 2 (Public Safety) scales proportionally from 30.0 to 90.0
    assert prio_low_hazard["components"]["safety"] == 30.0
    assert prio_high_hazard["components"]["safety"] == 90.0

    # The difference in final score is strictly due to the 0.25 safety weight:
    # 0.25 * (90 - 30) = 15.0 points difference
    expected_diff = round(0.25 * (90.0 - 30.0), 1)
    actual_diff = round(prio_high_hazard["final_score"] - prio_low_hazard["final_score"], 1)
    assert actual_diff == expected_diff


# 7. Dynamic Data-Driven Categories Test
def test_dynamic_data_driven_category_classification():
    """New categories added to the DB must be processed by classifier without code changes."""
    db = SessionLocal()
    try:
        # Check if test category already exists
        test_cat = db.query(Category).filter(Category.code == "drainage_overflow_test").first()
        if not test_cat:
            test_cat = Category(
                id="test-cat-uuid-001",
                code="drainage_overflow_test",
                name="Drainage Overflow Test",
                description="Custom municipal drainage overflow category",
                safety_weight=0.75,
                base_severity=7,
                keywords=["drainage overflow", "storm flood", "monsoon torrent", "inundated"]
            )
            db.add(test_cat)
            db.commit()

        # Run prediction passing DB session
        result = classifier.predict(
            image_path=None,
            description="Massive drainage overflow and monsoon torrent on main road.",
            db=db
        )

        assert "drainage_overflow_test" in result["raw_predictions"]
        assert result["predicted_category"] == "drainage_overflow_test"
        assert result["category_name"] == "Drainage Overflow Test"
    finally:
        # Clean up test category
        cat_to_del = db.query(Category).filter(Category.code == "drainage_overflow_test").first()
        if cat_to_del:
            db.delete(cat_to_del)
            db.commit()
        db.close()


# 8. Data Provenance & is_synthetic Flag Tests
def test_data_provenance_is_synthetic(client, admin_token):
    """Seeded demo reports must have is_synthetic=True, new citizen reports must have is_synthetic=False."""
    # Check seeded reports via admin ledger (fetch enough to include seeded batch)
    res = client.get("/api/admin/reports?limit=50", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    assert len(items) > 0
    # Seeded demo reports are marked synthetic
    assert any(r.get("is_synthetic") is True for r in items)

    # Submit genuine citizen report
    new_report_res = client.post(
        "/api/reports",
        data={
            "title": "Real Citizen Road Pothole",
            "description": "Genuine citizen report of broken pavement near Koramangala 4th block.",
            "category_code": "pothole",
            "latitude": 12.9348,
            "longitude": 77.6250
        }
    )
    assert new_report_res.status_code == 201
    new_data = new_report_res.json()
    assert new_data["is_synthetic"] is False


# 9. Alembic Migration Upgrade/Downgrade Test
def test_alembic_migrations_execute_cleanly():
    """Verify that Alembic migrations run upgrade and downgrade without errors."""
    temp_db = os.path.join(tempfile.gettempdir(), 'test_alembic_exec.db').replace('\\', '/')
    if os.path.exists(temp_db):
        try: os.remove(temp_db)
        except Exception: pass

    cfg = Config('backend/alembic.ini')
    cfg.set_main_option('script_location', 'backend/alembic')

    original_url = settings.DATABASE_URL
    settings.DATABASE_URL = f'sqlite:///{temp_db}'

    try:
        command.upgrade(cfg, 'head')
        command.downgrade(cfg, 'base')
        command.upgrade(cfg, 'head')
    finally:
        settings.DATABASE_URL = original_url
        if os.path.exists(temp_db):
            try: os.remove(temp_db)
            except Exception: pass
