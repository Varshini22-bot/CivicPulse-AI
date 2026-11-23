import os
import uuid
import tempfile
import pytest
from PIL import Image
from sqlalchemy.orm import Session
from app.models import Report, Category
from app.services.resolution_verification_service import ResolutionVerificationService
from app.services.privacy_service import PrivacyService


def test_resolution_verification_missing_images(db_session: Session):
    """Verifies that missing before or after images result in unverifiable status without crashing."""
    cat = db_session.query(Category).first()
    if not cat:
        cat = Category(name="Roads & Footpaths", code=f"pothole_{uuid.uuid4().hex[:6]}")
        db_session.add(cat)
        db_session.flush()

    report = Report(
        tracking_number=f"CP-TEST-{uuid.uuid4().hex[:8]}",
        title="Pothole Test",
        description="Pothole description",
        latitude=12.9716,
        longitude=77.5946,
        category_id=cat.id,
        image_url=None
    )
    db_session.add(report)
    db_session.flush()

    res = ResolutionVerificationService.verify_resolution(
        db=db_session,
        report=report,
        resolution_image_url=None,
        resolution_latitude=12.9716,
        resolution_longitude=77.5946
    )

    assert res["status"] == "unverifiable"
    assert res["verification_score"] == 0.0
    assert "missing" in res["reasons"][0].lower()


def test_resolution_verification_with_images(db_session: Session):
    """Verifies resolution verification with real image files on disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        before_path = os.path.join(tmpdir, "before.jpg")
        after_path = os.path.join(tmpdir, "after.jpg")

        # Create two simple test images
        img_before = Image.new("RGB", (224, 224), color=(100, 100, 100))
        img_before.save(before_path)

        img_after = Image.new("RGB", (224, 224), color=(105, 105, 105))
        img_after.save(after_path)

        cat = db_session.query(Category).first()
        if not cat:
            cat = Category(name="Roads & Footpaths", code=f"pothole_{uuid.uuid4().hex[:6]}")
            db_session.add(cat)
            db_session.flush()

        report = Report(
            tracking_number=f"CP-TEST-{uuid.uuid4().hex[:8]}",
            title="Pothole Test with Images",
            description="Fix required",
            latitude=12.9716,
            longitude=77.5946,
            image_url=before_path,
            category_id=cat.id
        )
        report.category = cat
        db_session.add(report)
        db_session.flush()

        # 1. Close distance resolution (10 meters away)
        res = ResolutionVerificationService.verify_resolution(
            db=db_session,
            report=report,
            resolution_image_url=after_path,
            resolution_latitude=12.97168,
            resolution_longitude=77.59465
        )

        assert res["status"] in ["verified", "flagged_for_review"]
        assert 0.0 <= res["verification_score"] <= 1.0
        assert res["gps_distance_meters"] is not None
        assert res["gps_distance_meters"] < 20.0
        assert len(res["reasons"]) > 0

        # 2. Far distance resolution (500 meters away -> should flag)
        res_far = ResolutionVerificationService.verify_resolution(
            db=db_session,
            report=report,
            resolution_image_url=after_path,
            resolution_latitude=12.9760,
            resolution_longitude=77.5946
        )

        assert res_far["gps_distance_meters"] > 400.0
        assert any("GPS warning" in r or "mismatch" in r for r in res_far["reasons"])


def test_privacy_anonymization():
    """Verifies that PrivacyService processes images safely without throwing exceptions."""
    # Test nonexistent path
    nonexistent = PrivacyService.anonymize_image("nonexistent_path_xyz.jpg")
    assert nonexistent["anonymized"] is False

    # Test real synthetic image
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "test_privacy.jpg")
        img = Image.new("RGB", (200, 200), color=(128, 128, 128))
        img.save(test_path)

        res = PrivacyService.anonymize_image(test_path)
        assert isinstance(res, dict)
        assert "anonymized" in res
        assert "faces_detected" in res
        assert "plates_detected" in res
        assert os.path.exists(test_path)


def test_privacy_face_detection_and_redaction():
    """
    Verifies that PrivacyService correctly loads the bundled OpenCV Haar cascade
    (haarcascade_frontalface_default.xml, BSD-3-Clause) and detects + blurs
    a synthetic human face pattern while documenting that plate redaction is not implemented.
    """
    import cv2
    import numpy as np

    # Verify cascade file exists at bundled repo path
    cascade = PrivacyService._get_face_cascade()
    assert cascade is not None
    assert not cascade.empty()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "synthetic_face.png")

        # Create a synthetic face drawing fixture
        img = np.ones((300, 300, 3), dtype=np.uint8) * 220
        cv2.ellipse(img, (150, 150), (80, 100), 0, 0, 360, (180, 180, 180), -1)  # Head oval
        cv2.ellipse(img, (120, 130), (15, 8), 0, 0, 360, (40, 40, 40), -1)        # Left eye
        cv2.ellipse(img, (180, 130), (15, 8), 0, 0, 360, (40, 40, 40), -1)        # Right eye
        cv2.line(img, (105, 115), (135, 118), (30, 30, 30), 4)                    # Left eyebrow
        cv2.line(img, (195, 115), (165, 118), (30, 30, 30), 4)                    # Right eyebrow
        cv2.line(img, (150, 130), (150, 170), (120, 120, 120), 4)                 # Nose bridge
        cv2.line(img, (140, 170), (160, 170), (80, 80, 80), 3)                    # Nose base
        cv2.ellipse(img, (150, 205), (30, 10), 0, 0, 360, (50, 50, 50), -1)      # Mouth
        cv2.line(img, (130, 205), (170, 205), (20, 20, 20), 2)                    # Lip line

        cv2.imwrite(test_path, img)
        original_bytes = os.path.getsize(test_path)

        res = PrivacyService.anonymize_image(test_path)

        # Assert face detected and anonymized
        assert res["anonymized"] is True
        assert res["faces_detected"] >= 1
        # Explicit check: license plate redaction is NOT implemented
        assert res["plates_detected"] == 0
        assert res["plate_redaction_implemented"] is False
        assert "Plate redaction not implemented" in res["note"]
        assert os.path.exists(res["saved_path"])
