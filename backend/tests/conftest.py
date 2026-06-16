"""Integration test fixtures.

These tests run against a RUNNING api (docker compose up, TEST_MODE=true).
Configure via env:
  API_BASE       (default http://localhost:8000)   # use .../api behind nginx
  ADMIN_USERNAME (default admin)
  ADMIN_PASSWORD (default change_me_strong_password)
"""
import os

import httpx
import pytest

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change_me_strong_password")


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=API_BASE, timeout=60) as c:
        yield c


@pytest.fixture(scope="session")
def tokens(client):
    r = client.post(
        "/auth/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="session")
def auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture(scope="session", autouse=True)
def ensure_data(client, auth):
    """Make sure at least one pipeline run has populated jobs (TEST_MODE)."""
    client.post("/admin/run-now", headers=auth)
