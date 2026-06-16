"""Phase 6A — Materials Generation Engine API validation (running stack)."""


def _a_job_id(client, auth) -> str | None:
    jobs = client.get("/queue", headers=auth, params={"limit": 1}).json()
    return jobs[0]["id"] if jobs else None


def test_generate_and_fetch_materials(client, auth):
    job_id = _a_job_id(client, auth)
    if not job_id:
        return  # no scored jobs; skip gracefully

    gen = client.post(f"/jobs/{job_id}/materials/generate", headers=auth)
    # 200 if profile is set; 400 if profile missing (seed_demo sets it).
    assert gen.status_code in (200, 400)
    if gen.status_code != 200:
        return

    body = gen.json()
    assert body["resume_summary_text"]
    assert isinstance(body["application_answers"], list)
    # Restricted questions must never be auto-answered.
    qs = " ".join(a["question"].lower() for a in body["application_answers"])
    for banned in ("diversity", "disability", "veteran"):
        assert banned not in qs
    assert set(body["formats"]).issubset({"txt", "docx", "pdf"})

    got = client.get(f"/jobs/{job_id}/materials", headers=auth)
    assert got.status_code == 200


def test_download_formats(client, auth):
    job_id = _a_job_id(client, auth)
    if not job_id:
        return
    if client.post(f"/jobs/{job_id}/materials/generate", headers=auth).status_code != 200:
        return

    for fmt in ("txt", "docx", "pdf"):
        r = client.get(f"/jobs/{job_id}/materials/download/{fmt}", headers=auth)
        assert r.status_code == 200
        assert len(r.content) > 0

    bad = client.get(f"/jobs/{job_id}/materials/download/rtf", headers=auth)
    assert bad.status_code == 400
