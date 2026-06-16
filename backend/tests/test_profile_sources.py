"""Profile, resumes-summary, and sources validation."""


def test_sources_listed(client, auth):
    r = client.get("/sources", headers=auth)
    assert r.status_code == 200
    names = {s["name"] for s in r.json()}
    # Default seeded ATS sources should be present.
    assert {"greenhouse", "lever", "ashby"}.issubset(names)


def test_sources_require_auth(client):
    assert client.get("/sources").status_code == 401


def test_profile_get_or_absent(client, auth):
    r = client.get("/profile", headers=auth)
    # 200 if seeded (demo), 404 if not — both are valid contract responses.
    assert r.status_code in (200, 404)


def test_profile_upsert_roundtrip(client, auth):
    payload = {
        "full_name": "Tamalampudi Sameer Reddy",
        "email": "sameerreddy213@gmail.com",
        "phone": "+91 9652877199",
        "location": "Andhra Pradesh, India",
        "notice_period": "Immediate",
        "experience_level": "Fresher",
        "work_auth": "India",
        "relocation": True,
        "expected_ctc": "8 LPA",
    }
    put = client.put("/profile", headers=auth, json=payload)
    assert put.status_code == 200
    assert put.json()["full_name"] == payload["full_name"]

    got = client.get("/profile", headers=auth)
    assert got.status_code == 200
    assert got.json()["email"] == payload["email"]


def test_resumes_summary_shape(client, auth):
    r = client.get("/resumes/summary", headers=auth)
    assert r.status_code == 200
    for row in r.json():
        assert "category" in row
        assert "previous_versions" in row
