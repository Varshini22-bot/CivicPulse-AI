import uuid
import pytest
from app.services.geospatial_service import GeospatialService
from app.services.recurrence_service import RecurrenceService
from app.services.routing_service import RoutingService
from app.models import Report, Category, RoadSegment


def test_hdbscan_hotspots_detection(db_session):
    """Verify HDBSCAN hierarchical clustering produces valid clusters with stability scores."""
    cat = db_session.query(Category).first()
    
    # Create a dense cluster of reports in Koramangala
    base_lat, base_lon = 12.9348, 77.6250
    for i in range(5):
        r = Report(
            tracking_number=f"CP-HDB-{uuid.uuid4().hex[:8]}",
            title=f"Cluster Issue {i}",
            description="Dense cluster issue",
            category_id=cat.id,
            latitude=base_lat + (i * 0.0002),
            longitude=base_lon + (i * 0.0002),
            area="Koramangala",
            status="Submitted",
            priority_score=75.0,
            priority_level="High"
        )
        db_session.add(r)
    db_session.commit()

    hotspots = GeospatialService.detect_hotspots(
        db=db_session,
        algorithm="hdbscan",
        min_cluster_size=3,
        min_samples=2
    )

    assert len(hotspots) > 0
    hs = hotspots[0]
    assert hs["algorithm"] == "hdbscan"
    assert "cluster_stability_score" in hs
    assert "temporal_weighted_activity" in hs
    assert hs["radius_meters"] > 0


def test_osm_road_network_seeding_and_snapping(db_session):
    """Verify OpenStreetMap road segments are seeded and reports snap to nearest line segment."""
    seeded = RecurrenceService.seed_osm_road_network(db_session, "data/osm/bengaluru_roads.json")
    # Should seed segments or have existing ones
    total_segs = db_session.query(RoadSegment).count()
    assert total_segs >= 10

    # Test coordinate on Koramangala 80ft road (waypoint 12.9348, 77.6220)
    seg, dist = RecurrenceService.snap_point_to_segment(db_session, 12.9348, 77.6220, max_snap_meters=50.0)
    assert seg is not None
    assert "80 Feet Road" in seg.name
    assert dist <= 50.0


def test_recurring_failure_detection_and_advisory(db_session):
    """Verify that 3+ reports on the same road segment trigger recurring failure advisory."""
    cat = db_session.query(Category).filter(Category.code == "pothole").first() or db_session.query(Category).first()
    seg = db_session.query(RoadSegment).first()
    assert seg is not None

    # Add 3 reports on this road segment
    for i in range(3):
        r = Report(
            tracking_number=f"CP-REC-{uuid.uuid4().hex[:8]}",
            title=f"Chronic Defect {i}",
            description="Recurring road failure",
            category_id=cat.id,
            road_segment_id=seg.id,
            latitude=12.9348,
            longitude=77.6250,
            status="Submitted",
            priority_score=80.0,
            priority_level="High"
        )
        db_session.add(r)
    db_session.commit()

    failures = RecurrenceService.detect_recurring_failures(
        db=db_session,
        min_incident_count=3,
        time_window_days=90
    )

    assert len(failures) > 0
    matched = [f for f in failures if f["road_segment_id"] == seg.id]
    assert len(matched) > 0
    corridor = matched[0]
    assert corridor["incident_count"] >= 3
    assert "sub-base" in corridor["advisory_recommendation"].lower() or "root" in corridor["advisory_recommendation"].lower()
    assert "OpenStreetMap" in corridor["attribution"]


def test_google_ortools_dispatch_route_optimization(db_session):
    """Verify TSP dispatch route optimization returns valid ordered sequence and distance."""
    reports = db_session.query(Report).limit(5).all()
    assert len(reports) >= 3

    route_plan = RoutingService.optimize_dispatch_route(reports)
    assert route_plan["total_stops"] >= 4  # depot + inspections
    assert route_plan["total_distance_km"] > 0.0
    assert route_plan["estimated_total_duration_minutes"] > 0.0
    assert len(route_plan["ordered_stops"]) == route_plan["total_stops"]
    assert route_plan["ordered_stops"][0]["location_type"] == "depot"


def test_map_api_v2_endpoints(client):
    """Test map API endpoints for HDBSCAN hotspots, recurring failures, and dispatch route."""
    # 1. Hotspots with HDBSCAN
    h_res = client.get("/api/map/hotspots?algorithm=hdbscan")
    assert h_res.status_code == 200
    assert isinstance(h_res.json(), list)

    # 2. Recurring failures
    r_res = client.get("/api/map/recurring-failures?min_incidents=2")
    assert r_res.status_code == 200
    assert isinstance(r_res.json(), list)

    # 3. Dispatch route
    d_res = client.get("/api/map/dispatch-route?max_stops=5")
    assert d_res.status_code == 200
    route_data = d_res.json()
    assert "ordered_stops" in route_data
    assert "total_distance_km" in route_data
