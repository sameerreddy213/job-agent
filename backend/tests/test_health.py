def test_health_public(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_db(client):
    r = client.get("/health/db")
    assert r.status_code == 200
    assert r.json()["db"] == "up"


def test_health_sources_requires_auth(client):
    r = client.get("/health/sources")
    assert r.status_code == 401


def test_health_sources(client, auth):
    r = client.get("/health/sources", headers=auth)
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    if rows:
        assert rows[0]["status"] in ("HEALTHY", "WARNING", "FAILED")
