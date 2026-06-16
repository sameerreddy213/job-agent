"""Phase 6C — Telegram settings + metrics validation (running stack)."""


def test_telegram_settings_get(client, auth):
    r = client.get("/settings/telegram", headers=auth)
    assert r.status_code == 200
    body = r.json()
    for key in ("enabled", "configured", "pref_high_match", "pref_security"):
        assert key in body


def test_telegram_settings_update(client, auth):
    r = client.put(
        "/settings/telegram",
        headers=auth,
        json={"enabled": False, "chat_id": "123456", "pref_daily": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["chat_id"] == "123456"
    assert body["pref_daily"] is False


def test_metrics_include_telegram_counters(client):
    r = client.get("/metrics.json")
    assert r.status_code == 200
    m = r.json()
    for key in ("telegram_sent", "telegram_failed", "telegram_retried", "sheet_latency_ms"):
        assert key in m


def test_telegram_settings_requires_auth(client):
    assert client.get("/settings/telegram").status_code == 401
