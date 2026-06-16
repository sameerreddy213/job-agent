def test_analytics_overview(client, auth):
    r = client.get("/analytics/overview", headers=auth, params={"days": 30, "top_n": 10})
    assert r.status_code == 200
    body = r.json()
    for key in (
        "jobs_per_day",
        "applications_per_day",
        "top_companies",
        "top_locations",
        "top_skills",
        "resume_stats",
        "interview_conversion_rate",
    ):
        assert key in body, f"missing analytics field: {key}"
    assert isinstance(body["top_companies"], list)


def test_dashboard_summary(client, auth):
    r = client.get("/dashboard/summary", headers=auth)
    assert r.status_code == 200
    body = r.json()
    for key in ("total_jobs", "new_today", "auto_eligible", "review_queue", "rejected"):
        assert key in body
    assert body["total_jobs"] >= 0
