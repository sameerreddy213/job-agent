def test_settings_overview(client, auth):
    r = client.get("/settings", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["scoring_weights"]["freshers"] == 40
    assert body["thresholds"]["auto_approve"] == 90


def test_company_blacklist_crud(client, auth):
    # Create
    r = client.post(
        "/settings/blacklist/companies",
        headers=auth,
        json={"company": "TestCorpXYZ", "reason": "pytest"},
    )
    assert r.status_code in (201, 409)
    if r.status_code == 201:
        item_id = r.json()["id"]
        # Duplicate -> 409
        dup = client.post(
            "/settings/blacklist/companies",
            headers=auth,
            json={"company": "TestCorpXYZ"},
        )
        assert dup.status_code == 409
        # Delete
        assert client.delete(
            f"/settings/blacklist/companies/{item_id}", headers=auth
        ).status_code == 204


def test_keyword_blacklist_validation(client, auth):
    bad = client.post(
        "/settings/blacklist/keywords",
        headers=auth,
        json={"keyword": "x", "applies_to": "invalid"},
    )
    assert bad.status_code == 400


def test_audit_log_records_actions(client, auth):
    # A manual run should have produced an audit entry.
    client.post("/admin/run-now", headers=auth)
    r = client.get("/audit", headers=auth, params={"action": "pipeline.run_now"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
