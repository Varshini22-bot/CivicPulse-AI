import uuid
import pytest
import numpy as np
from app.services.duplicate_service import DuplicateService
from app.services.embedding_service import EmbeddingService
from app.models import Report, Category, DuplicateCandidate, User
from app.core.config import settings


def test_clip_cosine_similarity_exact():
    """Verify L2-normalized cosine similarity computation."""
    # Orthogonal vectors -> 0.0
    u = [1.0] + [0.0] * 511
    v = [0.0, 1.0] + [0.0] * 510
    assert EmbeddingService.cosine_similarity(u, v) == 0.0

    # Identical vectors -> 1.0
    assert EmbeddingService.cosine_similarity(u, u) == 1.0

    # Missing vector returns None (honest missingness, never fake 0.5)
    assert EmbeddingService.cosine_similarity(u, None) is None
    assert EmbeddingService.cosine_similarity(None, v) is None


def test_spatial_gate_with_gps_margin():
    """Verify that candidate filtering enforces category radius + GPS accuracy margin."""
    cat_code = "pothole"
    base_radius = settings.DUPLICATE_CATEGORY_RADII[cat_code]  # 25m
    effective_radius = DuplicateService.get_effective_radius(cat_code)  # 25 + 10 = 35m
    assert effective_radius == base_radius + settings.GPS_ACCURACY_MARGIN_METERS

    # Within base radius
    assert DuplicateService.is_within_category_radius(20.0, cat_code) is True
    # Inside GPS margin buffer (30m is >25m base, but <=35m effective)
    assert DuplicateService.is_within_category_radius(30.0, cat_code, include_gps_margin=True) is True
    # Outside margin buffer (>35m)
    assert DuplicateService.is_within_category_radius(40.0, cat_code, include_gps_margin=True) is False


def test_weight_renormalization_missing_visual_v2(db_session):
    """When both CLIP and pHash are absent, weights must renormalize across remaining factors."""
    cat = db_session.query(Category).filter(Category.code == "pothole").first() or db_session.query(Category).first()

    r1 = Report(
        tracking_number=f"CP-DUP-{uuid.uuid4().hex[:8]}",
        title="Test Report 1",
        description="Pothole in Koramangala",
        category_id=cat.id,
        latitude=12.9348,
        longitude=77.6250
    )
    r2 = Report(
        tracking_number=f"CP-DUP-{uuid.uuid4().hex[:8]}",
        title="Test Report 2",
        description="Duplicate pothole nearby",
        category_id=cat.id,
        latitude=12.9349,  # ~15 meters away
        longitude=77.6251
    )
    db_session.add_all([r1, r2])
    db_session.flush()

    res = DuplicateService.evaluate_duplicate_pair(
        r1, r2,
        p_hash_a=None, p_hash_b=None,
        emb_a=None, emb_b=None
    )

    assert res["visual_similarity"] is None
    assert res["clip_similarity"] is None
    assert res["phash_similarity"] is None
    assert 0.0 <= res["composite_score"] <= 1.0
    assert res["is_duplicate_candidate"] is True


def test_duplicate_resolution_logs_feedback(client, admin_token, db_session):
    """Resolving a duplicate candidate logs human feedback for model fine-tuning."""
    cat = db_session.query(Category).first()
    r1 = Report(tracking_number=f"CP-DUP-{uuid.uuid4().hex[:8]}", title="Report A", description="Desc", category_id=cat.id, latitude=12.93, longitude=77.62)
    r2 = Report(tracking_number=f"CP-DUP-{uuid.uuid4().hex[:8]}", title="Report B", description="Desc", category_id=cat.id, latitude=12.9301, longitude=77.6201)
    db_session.add_all([r1, r2])
    db_session.flush()

    cand = DuplicateCandidate(
        source_report_id=r1.id,
        target_report_id=r2.id,
        distance_meters=18.5,
        category_match=True,
        time_diff_hours=1.2,
        clip_similarity=0.88,
        phash_similarity=0.85,
        composite_score=0.82,
        status="suggested"
    )
    db_session.add(cand)
    db_session.commit()

    res = client.post(
        f"/api/admin/duplicates/{cand.id}/resolve",
        json={"status": "confirmed", "notes": "Verified by field coordinator: same pothole."},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["resolved_status"] == "confirmed"
    assert data["feedback_logged"] is True

    # Verify feedback was stored in DB
    db_session.refresh(cand)
    assert cand.status == "confirmed"
    assert cand.resolution_feedback is not None
    assert cand.resolution_feedback["decision"] == "confirmed"
    assert cand.resolution_feedback["features_at_resolution"]["clip_similarity"] == 0.88
