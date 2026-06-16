"""Phase 7A — Workflow engine validation."""
from app.workflow import State, can_transition


# --------------------------- unit (no server) --------------------------- #
def test_valid_transitions():
    assert can_transition(State.REVIEW_QUEUE, State.APPROVED)
    assert can_transition(State.REVIEW_QUEUE, State.REJECTED)
    assert can_transition(State.SCORED, State.REVIEW_QUEUE)
    assert can_transition(State.APPROVED, State.MATERIALS_GENERATED)


def test_invalid_transitions():
    assert not can_transition(State.FILTERED, State.APPROVED)
    assert not can_transition(State.ARCHIVED, State.REVIEW_QUEUE)
    assert not can_transition(State.APPLIED, State.APPROVED)


# --------------------------- API (running stack) --------------------------- #
def test_state_counts(client, auth):
    r = client.get("/workflow/state-counts", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert "REVIEW_QUEUE" in body and "ARCHIVED" in body


def test_approve_then_history(client, auth):
    jobs = client.get("/queue", headers=auth, params={"limit": 1}).json()
    if not jobs:
        return
    job_id = jobs[0]["id"]

    appr = client.post(f"/jobs/{job_id}/approve", headers=auth)
    assert appr.status_code == 200
    assert appr.json()["status"] == "APPROVED"

    # Approving again is an illegal transition (APPROVED -> APPROVED).
    again = client.post(f"/jobs/{job_id}/approve", headers=auth)
    assert again.status_code == 409

    hist = client.get(f"/jobs/{job_id}/workflow/history", headers=auth)
    assert hist.status_code == 200
    transitions = hist.json()
    assert any(h["new_state"] == "APPROVED" for h in transitions)


def test_archive_and_pending_review(client, auth):
    jobs = client.get("/workflow/pending-review", headers=auth, params={"limit": 1}).json()
    if not jobs:
        return
    job_id = jobs[0]["id"]
    arch = client.post(f"/jobs/{job_id}/archive", headers=auth)
    assert arch.status_code == 200
    assert arch.json()["status"] == "ARCHIVED"


def test_bulk_reject(client, auth):
    jobs = client.get("/queue", headers=auth, params={"limit": 3}).json()
    ids = [j["id"] for j in jobs]
    if not ids:
        return
    r = client.post("/jobs/bulk/reject", headers=auth, json={"ids": ids})
    assert r.status_code == 200
    assert r.json()["succeeded"] >= 1
