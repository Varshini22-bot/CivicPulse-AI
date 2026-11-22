import pytest
import os
import sys
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.database.connection import SessionLocal, Base, engine
from app.database.seed_data import seed_database

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def admin_token(client):
    res = client.post("/api/auth/login", json={
        "email": "admin@civicpulse.gov.in",
        "password": "Admin@12345"
    })
    assert res.status_code == 200, res.text
    return res.json()["access_token"]

@pytest.fixture
def citizen_token(client):
    res = client.post("/api/auth/login", json={
        "email": "citizen@example.com",
        "password": "Citizen@12345"
    })
    assert res.status_code == 200, res.text
    return res.json()["access_token"]
