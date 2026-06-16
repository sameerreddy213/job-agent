import os

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change_me_strong_password")


def test_login_success(client):
    r = client.post("/auth/login", data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["refresh_token"]


def test_login_bad_credentials(client):
    r = client.post("/auth/login", data={"username": ADMIN_USERNAME, "password": "wrong"})
    assert r.status_code == 401


def test_me(client, auth):
    r = client.get("/auth/me", headers=auth)
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_protected_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_refresh_rotation(client):
    login = client.post(
        "/auth/login", data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    ).json()
    old_refresh = login["refresh_token"]

    r = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 200
    new = r.json()
    assert new["refresh_token"] != old_refresh

    # Old refresh token is now revoked.
    again = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert again.status_code == 401


def test_logout_revokes(client):
    login = client.post(
        "/auth/login", data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    ).json()
    refresh = login["refresh_token"]
    assert client.post("/auth/logout", json={"refresh_token": refresh}).status_code == 204
    assert client.post("/auth/refresh", json={"refresh_token": refresh}).status_code == 401


def test_refresh_reuse_detection(client):
    # Fresh session.
    login = client.post(
        "/auth/login", data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    ).json()
    old = login["refresh_token"]

    # Rotate once -> old token is now revoked, new token is valid.
    rotated = client.post("/auth/refresh", json={"refresh_token": old}).json()
    new = rotated["refresh_token"]

    # Reusing the OLD (already-rotated) token = reuse detection -> 401.
    reuse = client.post("/auth/refresh", json={"refresh_token": old})
    assert reuse.status_code == 401

    # The whole family is revoked, so the NEW token no longer works either.
    after = client.post("/auth/refresh", json={"refresh_token": new})
    assert after.status_code == 401


def test_rate_limit_lockout(client):
    # Use a throwaway username so we never lock the real admin account.
    probe = "ratelimit_probe_user"
    statuses = [
        client.post("/auth/login", data={"username": probe, "password": "x"}).status_code
        for _ in range(7)
    ]
    assert 429 in statuses, f"expected a 429 lockout, got {statuses}"
