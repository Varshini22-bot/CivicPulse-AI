def test_login_success(client):
    res = client.post("/api/auth/login", json={
        "email": "admin@civicpulse.gov.in",
        "password": "Admin@12345"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "admin"

def test_login_invalid_credentials(client):
    res = client.post("/api/auth/login", json={
        "email": "admin@civicpulse.gov.in",
        "password": "WrongPassword!"
    })
    assert res.status_code == 401

def test_citizen_registration(client):
    import uuid
    rand_email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    res = client.post("/api/auth/register", json={
        "email": rand_email,
        "password": "SecurePassword123",
        "full_name": "Test Citizen",
        "phone": "+91-99999-00000"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["user"]["email"] == rand_email
    assert data["user"]["role"] == "citizen"

def test_auth_me(client, citizen_token):
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {citizen_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "citizen@example.com"
    assert data["role"] == "citizen"
