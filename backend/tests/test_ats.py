"""Phase 8B — ATS integration layer validation.

Required verification areas:
  1. ATS detection validation     (pure unit)
  2. Readiness scoring validation  (pure unit)
  3. Dashboard validation          (API, running stack)
"""
from app.ats import (
    ALL_ATS_TYPES,
    AtsType,
    detect_ats,
    evaluate_readiness,
)


# --------------------------- 1. ATS detection --------------------------- #
def test_detect_known_hosts():
    cases = {
        "https://boards.greenhouse.io/acme/jobs/123": AtsType.GREENHOUSE,
        "https://jobs.lever.co/netflix/abc": AtsType.LEVER,
        "https://jobs.ashbyhq.com/openai/xyz": AtsType.ASHBY,
        "https://acme.wd1.myworkdayjobs.com/careers/job/123": AtsType.WORKDAY,
        "https://jobs.smartrecruiters.com/Acme/12345": AtsType.SMARTRECRUITERS,
        "https://jobs.jobvite.com/acme/job/abc": AtsType.JOBVITE,
        "https://acme.bamboohr.com/jobs/view.php?id=9": AtsType.BAMBOOHR,
    }
    for url, expected in cases.items():
        assert detect_ats(url).ats_type == expected, url


def test_detect_custom_vs_unknown():
    # Real URL, unrecognised host -> CUSTOM.
    assert detect_ats("https://careers.acme.com/apply/42").ats_type == AtsType.CUSTOM
    # No URL at all -> UNKNOWN.
    assert detect_ats(None).ats_type == AtsType.UNKNOWN
    assert detect_ats("").ats_type == AtsType.UNKNOWN


def test_detect_source_fallback_when_no_url():
    assert detect_ats(None, source="greenhouse").ats_type == AtsType.GREENHOUSE
    assert detect_ats(None, source="lever").ats_type == AtsType.LEVER
    assert detect_ats(None, source="ashby").ats_type == AtsType.ASHBY
    assert detect_ats(None, source="mystery").ats_type == AtsType.UNKNOWN


def test_workday_version_extracted():
    det = detect_ats("https://acme.wd3.myworkdayjobs.com/en-US/careers/job/1")
    assert det.ats_type == AtsType.WORKDAY
    assert det.ats_version == "wd3"


def test_capabilities_consistent():
    # Clean public boards support easy apply and need no manual fields.
    for url in ("https://boards.greenhouse.io/a/jobs/1", "https://jobs.lever.co/a/1"):
        d = detect_ats(url)
        assert d.supports_easy_apply and not d.requires_manual_fields
    # Portal-style ATSs require manual fields.
    d = detect_ats("https://acme.wd1.myworkdayjobs.com/x")
    assert d.requires_manual_fields and not d.supports_easy_apply
    # Every detection returns a known type.
    assert detect_ats("https://x.y/z").ats_type in ALL_ATS_TYPES


# --------------------------- 2. Readiness scoring --------------------------- #
def _ats(easy=True, manual=False, kind=AtsType.GREENHOUSE):
    return detect_ats("https://boards.greenhouse.io/a/jobs/1") if kind == AtsType.GREENHOUSE else detect_ats("https://acme.wd1.myworkdayjobs.com/x")


def test_full_packet_easy_ats_is_ready():
    r = evaluate_readiness(has_documents=True, resume_category="SDE", answer_count=3, ats=_ats())
    assert r.ready_score == 100
    assert r.ready is True
    assert not (r.missing_materials or r.missing_resume or r.missing_answers)
    assert r.manual_review_required is False


def test_missing_components_reduce_score():
    none = evaluate_readiness(has_documents=False, resume_category=None, answer_count=0, ats=_ats())
    assert none.ready_score == 0 and none.ready is False
    assert none.missing_materials and none.missing_resume and none.missing_answers

    only_docs = evaluate_readiness(has_documents=True, resume_category=None, answer_count=0, ats=_ats())
    assert only_docs.ready_score == 40  # materials weight
    assert not only_docs.ready

    no_answers = evaluate_readiness(has_documents=True, resume_category="SDE", answer_count=0, ats=_ats())
    assert no_answers.ready_score == 70  # materials + resume
    assert not no_answers.ready


def test_manual_ats_blocks_ready_even_when_complete():
    r = evaluate_readiness(
        has_documents=True, resume_category="SDE", answer_count=2,
        ats=detect_ats("https://acme.wd1.myworkdayjobs.com/x"),
    )
    assert r.ready_score == 100
    assert r.manual_review_required is True
    assert r.ready is False  # complete but needs manual fields


# --------------------------- 3. Dashboard validation (API) --------------------------- #
def _ensure_app(client, auth):
    jobs = client.get("/queue", headers=auth, params={"limit": 1}).json()
    if jobs:
        client.post(f"/jobs/{jobs[0]['id']}/approve", headers=auth)


def test_ats_breakdown_shape(client, auth):
    _ensure_app(client, auth)
    r = client.get("/applications/ats-breakdown", headers=auth)
    assert r.status_code == 200
    b = r.json()
    assert b["detected"] + b["unknown"] == b["total"]
    assert b["total"] == sum(c["count"] for c in b["by_ats"])
    assert b["ready_to_apply"] >= 0 and b["manual_review_required"] >= 0


def test_readiness_list_and_ready_queue(client, auth):
    _ensure_app(client, auth)
    full = client.get("/applications/readiness", headers=auth)
    assert full.status_code == 200
    for item in full.json():
        assert 0 <= item["ready_score"] <= 100
        assert "ats_type" in item

    queue = client.get("/applications/ready-queue", headers=auth)
    assert queue.status_code == 200
    assert all(i["ready"] for i in queue.json())


def test_application_readiness_detail(client, auth):
    apps = client.get("/applications", headers=auth, params={"limit": 1}).json()
    if not apps:
        return
    r = client.get(f"/applications/{apps[0]['id']}/readiness", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert set(["ready_score", "ready", "missing_materials", "manual_review_required"]) <= body.keys()


def test_metrics_expose_ats_counters(client, auth):
    text = client.get("/metrics", headers=auth).text
    for counter in ("ready_to_apply", "manual_review_required", "ats_detected", "ats_unknown"):
        assert counter in text
