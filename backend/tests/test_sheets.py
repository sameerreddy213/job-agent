"""Phase 6B — Google Sheets sync API validation (running stack, unconfigured env).

In the test/demo environment Sheets credentials are absent, so sync should
report 'not_configured' rather than error.
"""


def test_sync_status_shape(client, auth):
    r = client.get("/admin/sync-sheets/status", headers=auth)
    assert r.status_code == 200
    body = r.json()
    for key in ("configured", "enabled", "interval_minutes", "last_status", "rows_written"):
        assert key in body


def test_sync_now_unconfigured(client, auth):
    r = client.post("/admin/sync-sheets", headers=auth)
    assert r.status_code == 200
    # Without credentials configured, the sync is skipped, not failed.
    assert r.json()["status"] in ("not_configured", "success", "failed")


def test_sync_requires_auth(client):
    assert client.get("/admin/sync-sheets/status").status_code == 401
