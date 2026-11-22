import os
import pytest
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command


@pytest.mark.postgis
def test_postgis_migration_and_spatial_queries():
    """
    Integration test verifying PostGIS Geography column, GiST index, and ST_DWithin query.
    Skipped automatically when no PostgreSQL/PostGIS database is reachable.
    """
    postgis_url = os.environ.get(
        "POSTGIS_TEST_URL",
        "postgresql://civicpulse:civicpulse_secret@localhost:5432/civicpulse"
    )

    try:
        engine = create_engine(postgis_url, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            # Check if PostGIS extension is available
            res = conn.execute(text("SELECT PostGIS_Version()")).fetchone()
            assert res is not None, "PostGIS extension not responding"
    except Exception as e:
        pytest.skip(f"PostgreSQL/PostGIS not accessible ({e}). Set POSTGIS_TEST_URL to enable.")

    # 1. Run Alembic migrations on PostGIS database
    cfg = Config('backend/alembic.ini')
    cfg.set_main_option('script_location', 'backend/alembic')
    cfg.set_main_option('sqlalchemy.url', postgis_url)

    command.upgrade(cfg, 'head')

    with engine.connect() as conn:
        # 2. Verify column 'location' in 'reports' is of type geography(Point,4326)
        col_info = conn.execute(text("""
            SELECT udt_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'reports' AND column_name = 'location'
        """)).fetchone()
        assert col_info is not None, "Column 'location' not found in reports table"
        assert col_info[0] == "geography" or "USER-DEFINED" in col_info[1]

        # 3. Verify GiST spatial index exists
        idx_info = conn.execute(text("""
            SELECT indexdef FROM pg_indexes 
            WHERE tablename = 'reports' AND indexname = 'idx_reports_location_gist'
        """)).fetchone()
        assert idx_info is not None, "GiST spatial index 'idx_reports_location_gist' not found"
        assert "gist" in idx_info[0].lower(), f"Expected GiST index, got {idx_info[0]}"

        # 4. Insert two spatial points: Koramangala 5th Block and point ~15m away
        lat1, lon1 = 12.9352, 77.6245
        lat2, lon2 = 12.9353, 77.6246

        conn.execute(text("DELETE FROM reports WHERE tracking_number LIKE 'TEST-POSTGIS-%'"))
        conn.execute(text("""
            INSERT INTO reports (
                id, tracking_number, title, description, category_id,
                latitude, longitude, status, is_synthetic, location
            ) VALUES (
                'test-gis-1', 'TEST-POSTGIS-001', 'PostGIS Point A', 'Test location A', 'pothole',
                :lat1, :lon1, 'Submitted', true,
                ST_SetSRID(ST_MakePoint(:lon1, :lat1), 4326)::geography
            ), (
                'test-gis-2', 'TEST-POSTGIS-002', 'PostGIS Point B', 'Test location B', 'pothole',
                :lat2, :lon2, 'Submitted', true,
                ST_SetSRID(ST_MakePoint(:lon2, :lat2), 4326)::geography
            )
        """), {"lat1": lat1, "lon1": lon1, "lat2": lat2, "lon2": lon2})
        conn.commit()

        # 5. Execute ST_DWithin query: find points within 25 meters of Point A
        near_pts = conn.execute(text("""
            SELECT tracking_number, ST_Distance(location, ST_SetSRID(ST_MakePoint(:lon1, :lat1), 4326)::geography) AS dist_m
            FROM reports
            WHERE ST_DWithin(location, ST_SetSRID(ST_MakePoint(:lon1, :lat1), 4326)::geography, 25.0)
            ORDER BY dist_m ASC
        """), {"lat1": lat1, "lon1": lon1}).fetchall()

        assert len(near_pts) >= 2, f"Expected both points within 25m, found {len(near_pts)}"
        assert near_pts[0][0] == 'TEST-POSTGIS-001'
        assert round(near_pts[0][1], 1) == 0.0
        # Point B distance should be roughly ~15-18m
        assert 10.0 < near_pts[1][1] < 25.0

        # Cleanup test points
        conn.execute(text("DELETE FROM reports WHERE tracking_number LIKE 'TEST-POSTGIS-%'"))
        conn.commit()
