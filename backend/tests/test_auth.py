from __future__ import annotations


def test_login_success_viewer(client):
    response = client.post("/auth/login", json={"code": "11111111"})
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "viewer"
    assert body["expiresIn"] == 8 * 60 * 60
    assert body["token"]


def test_login_success_admin(client):
    response = client.post("/auth/login", json={"code": "99999999"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_login_failure(client):
    response = client.post("/auth/login", json={"code": "00000000"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_login_rate_limited_after_10_failures(client):
    for _ in range(10):
        client.post("/auth/login", json={"code": "wrong"})
    response = client.post("/auth/login", json={"code": "wrong"})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"


def test_successful_login_resets_failure_count(client):
    for _ in range(9):
        client.post("/auth/login", json={"code": "wrong"})
    ok = client.post("/auth/login", json={"code": "11111111"})
    assert ok.status_code == 200

    # 直前の失敗回数がリセットされているため、まだロックされない
    response = client.post("/auth/login", json={"code": "wrong"})
    assert response.status_code == 401


def test_protected_endpoint_without_token(client):
    response = client.get("/classes")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
