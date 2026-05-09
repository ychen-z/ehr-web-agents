from app.shared.seed import seed_local_users


def test_login_hrbp_success(client, db_session):
    seed_local_users(db_session)
    response = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_admin_success(client, db_session):
    seed_local_users(db_session)
    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "password123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client, db_session):
    seed_local_users(db_session)
    response = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "wrong"})
    assert response.status_code == 401


def test_login_unknown_user(client, db_session):
    seed_local_users(db_session)
    response = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    assert response.status_code == 401


def test_me_returns_current_user(client, db_session):
    seed_local_users(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]

    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "hrbp@example.com"
    assert data["role"] == "hrbp"


def test_me_rejects_missing_token(client, db_session):
    seed_local_users(db_session)
    response = client.get("/api/me")
    assert response.status_code == 401


def test_me_rejects_invalid_token(client, db_session):
    seed_local_users(db_session)
    response = client.get("/api/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert response.status_code == 401


def test_login_response_uses_access_token_not_token(client, db_session):
    seed_local_users(db_session)
    response = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token" not in data
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str) and len(data["access_token"]) > 0
