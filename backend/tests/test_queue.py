def test_run_now(client, auth):
    r = client.post("/admin/run-now", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert "runs" in body


def test_jobs_list(client, auth):
    r = client.get("/jobs", headers=auth, params={"limit": 10})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_queue_sorted_desc(client, auth):
    r = client.get("/queue", headers=auth, params={"limit": 50})
    assert r.status_code == 200
    jobs = r.json()
    scores = [j["score"]["total_score"] for j in jobs if j.get("score")]
    assert scores == sorted(scores, reverse=True), "queue must be score-descending"
    for j in jobs:
        assert j["status"] in ("AUTO_APPROVE_ELIGIBLE", "REVIEW_QUEUE")


def test_queue_counts(client, auth):
    r = client.get("/queue/counts", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert "auto_eligible" in body and "review_queue" in body


def test_min_score_filter(client, auth):
    r = client.get("/queue", headers=auth, params={"min_score": 90})
    assert r.status_code == 200
    for j in r.json():
        assert j["score"]["total_score"] >= 90


def test_job_detail(client, auth):
    listing = client.get("/jobs", headers=auth, params={"limit": 1}).json()
    if not listing:
        return
    job_id = listing[0]["id"]
    r = client.get(f"/jobs/{job_id}", headers=auth)
    assert r.status_code == 200
    assert r.json()["id"] == job_id


def test_dedup_no_duplicate_fingerprints(client, auth):
    jobs = client.get("/jobs", headers=auth, params={"limit": 200}).json()
    fps = [j["fingerprint"] for j in jobs]
    assert len(fps) == len(set(fps)), "duplicate fingerprints present"
