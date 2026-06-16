"""Phase 8C — manual apply assistant validation.

Required verification areas:
  1. Checklist validation
  2. Packet validation
  3. Download validation
  4. Ready queue validation

The packet builder (build_sections) is pure and unit-tested with stand-ins; the
checklist/packet/download/ready-queue flows are exercised against the API.
"""
from types import SimpleNamespace

from app.packet import build_sections


# --------------------------- 2a. Packet content (unit) --------------------------- #
def test_build_sections_includes_all_four_contents():
    app = SimpleNamespace(application_url="https://boards.greenhouse.io/a/jobs/1", notes="Call recruiter Monday")
    material = SimpleNamespace(
        cover_letter_text="Dear hiring manager...",
        resume_summary_text="Experienced fresher in React/Node.",
        application_answers=[{"question": "Why us?", "answer": "Great team."}],
    )
    job = SimpleNamespace(title="Frontend Developer", company="Acme")
    headings = [h for h, _ in build_sections(app, material, job)]
    assert "Cover Letter" in headings
    assert "Resume" in headings
    assert "Application Answers" in headings
    assert "Application Notes" in headings  # always present


def test_build_sections_notes_default_when_empty():
    app = SimpleNamespace(application_url=None, notes=None)
    material = SimpleNamespace(cover_letter_text=None, resume_summary_text="X", application_answers=[])
    sections = dict(build_sections(app, material, None))
    assert sections["Application Notes"] == "(none)"


# --------------------------- helpers (API) --------------------------- #
def _ready_application(client, auth):
    """Approve a job and return its application detail (materials may or may not exist)."""
    jobs = client.get("/queue", headers=auth, params={"limit": 1}).json()
    if not jobs:
        return None
    job_id = jobs[0]["id"]
    client.post(f"/jobs/{job_id}/approve", headers=auth)
    found = client.get("/applications", headers=auth, params={"job_id": job_id}).json()
    return found[0] if found else None


# --------------------------- 1. Checklist validation (API) --------------------------- #
def test_checklist_shape_and_completeness(client, auth):
    app = _ready_application(client, auth)
    if app is None:
        return
    r = client.get(f"/applications/{app['id']}/checklist", headers=auth)
    assert r.status_code == 200
    body = r.json()
    keys = {i["key"] for i in body["items"]}
    assert {"profile", "resume", "materials", "answers", "packet", "confirmed"} <= keys
    # complete == all required items done
    required_done = all(i["done"] for i in body["items"] if i["required"])
    assert body["complete"] == required_done
    # 'confirmed' starts not done.
    assert not body["ready_confirmed"]


# --------------------------- 2b. Packet generation (API) --------------------------- #
def test_packet_generation_and_status(client, auth):
    app = _ready_application(client, auth)
    if app is None:
        return
    aid = app["id"]
    # Only meaningful when materials were generated.
    if not app["material_id"]:
        bad = client.post(f"/applications/{aid}/packet", headers=auth)
        assert bad.status_code == 400
        return
    gen = client.post(f"/applications/{aid}/packet", headers=auth)
    assert gen.status_code == 200
    body = gen.json()
    assert body["generated"] is True
    assert set(body["formats"]) <= {"txt", "docx", "pdf"}
    assert len(body["formats"]) >= 1

    status = client.get(f"/applications/{aid}/packet", headers=auth)
    assert status.status_code == 200 and status.json()["generated"] is True


# --------------------------- 3. Download validation (API) --------------------------- #
def test_packet_download(client, auth):
    app = _ready_application(client, auth)
    if app is None or not app["material_id"]:
        return
    aid = app["id"]
    # Before generation a download 404s.
    pre = client.get(f"/applications/{aid}/packet/download/txt", headers=auth)
    assert pre.status_code in (200, 404)  # 200 if a previous test generated it

    client.post(f"/applications/{aid}/packet", headers=auth)
    ok = client.get(f"/applications/{aid}/packet/download/txt", headers=auth)
    assert ok.status_code == 200
    assert len(ok.content) > 0

    bad = client.get(f"/applications/{aid}/packet/download/rtf", headers=auth)
    assert bad.status_code == 400


# --------------------------- 4. Ready queue validation (API) --------------------------- #
def test_confirm_ready_and_metrics(client, auth):
    app = _ready_application(client, auth)
    if app is None:
        return
    aid = app["id"]
    r = client.post(f"/applications/{aid}/confirm-ready", headers=auth)
    assert r.status_code == 200
    assert r.json()["ready_confirmed"] is True

    # Idempotent.
    again = client.post(f"/applications/{aid}/confirm-ready", headers=auth)
    assert again.status_code == 200 and again.json()["ready_confirmed"] is True

    text = client.get("/metrics", headers=auth).text
    for counter in ("application_packets_generated", "application_packets_downloaded", "ready_to_apply_confirmed"):
        assert counter in text


def test_ready_queue_still_serves(client, auth):
    r = client.get("/applications/ready-queue", headers=auth)
    assert r.status_code == 200
    assert all(i["ready"] for i in r.json())
