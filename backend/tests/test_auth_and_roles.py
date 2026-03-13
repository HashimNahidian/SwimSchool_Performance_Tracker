def test_health_live(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_bootstrap_login_and_manager_access(client):
    bootstrap = client.post(
        "/auth/bootstrap-manager",
        json={
            "full_name": "Admin",
            "email": "admin@example.com",
            "password": "StrongPass123!",
            "role": "MANAGER",
            "is_active": True,
        },
    )
    assert bootstrap.status_code == 200, bootstrap.text

    login = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "StrongPass123!"},
    )
    assert login.status_code == 200, login.text
    token_payload = login.json()
    assert token_payload["access_token"]
    assert token_payload["refresh_token"]

    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["role"] == "MANAGER"

    manager_users = client.get(
        "/manager/users",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
    )
    assert manager_users.status_code == 200


def test_refresh_token_rotation(client):
    client.post(
        "/auth/bootstrap-manager",
        json={
            "full_name": "Admin",
            "email": "rotate@example.com",
            "password": "StrongPass123!",
            "role": "MANAGER",
            "is_active": True,
        },
    )
    login = client.post(
        "/auth/login",
        json={"email": "rotate@example.com", "password": "StrongPass123!"},
    )
    assert login.status_code == 200
    refresh = login.json()["refresh_token"]

    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert refresh_response.status_code == 200
    rotated = refresh_response.json()
    assert rotated["access_token"]
    assert rotated["refresh_token"]
    assert rotated["refresh_token"] != refresh

    replay = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert replay.status_code == 401
