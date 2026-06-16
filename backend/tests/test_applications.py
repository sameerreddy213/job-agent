"""Phase 8A — application engine validation.

Required verification areas:
  1. State transition validation
  2. Application analytics validation
  3. Material linkage validation
"""
from app.applications import (
    ALL_APP_STATES,
    AppState,
    VALID_APP_TRANSITIONS,
    can_transition,
)


# --------------------------- 1. State transitions (unit) --------------------------- #
def test_matrix_total_and_known():
    assert set(VALID_APP_TRANSITIONS.keys()) == ALL_APP_STATES
    for src, targets in VALID_APP_TRANSITIONS.items():
        assert src in ALL_APP_STATES
        for dst in targets:
            assert dst in ALL_APP_STATES
        assert src not in targets  # no self-loops


def test_terminal_states():
    for term in (AppState.REJECTED, AppState.ACCEPTED, AppState.WITHDRAWN):
        assert VALID_APP_TRANSITIONS[term] == set()


def test_withdraw_reachable_from_non_terminal():
    for state in ALL_APP_STATES:
        if VALID_APP_TRANSITIONS[state]:  # non-terminal
            assert AppState.WITHDRAWN in VALID_APP_TRANSITIONS[state]


def test_representative_transitions():
    assert can_transition(AppState.NOT_STARTED, AppState.READY)
    assert can_transition(AppState.READY, AppState.SUBMITTED)
    assert can_transition(AppState.SUBMITTED, AppState.INTERVIEW)
    assert can_transition(AppState.INTERVIEW, AppState.OFFER)
    assert can_transition(AppState.OFFER, AppState.ACCEPTED)
    # illegal
    assert not can_transition(AppState.NOT_STARTED, AppState.OFFER)
    assert not can_transition(AppState.REJECTED, AppState.INTERVIEW)
    assert not can_transition(AppState.ACCEPTED, AppState.SUBMITTED)
    assert not can_transition("BOGUS", AppState.READY)


# --------------------------- helpers (API) --------------------------- #
def _approved_application(client, auth):
    """Approve a queued job and return its provisioned application detail (or None)."""
    jobs = client.get("/queue", headers=auth, params={"limit": 1}).json()
    if not jobs:
        return None
    job_id = jobs[0]["id"]
    appr = client.post(f"/jobs/{job_id}/approve", headers=auth)
    if appr.status_code != 200:
        return None
    found = client.get("/applications", headers=auth, params={"job_id": job_id}).json()
    if not found:
        return None
    return client.get(f"/applications/{found[0]['id']}", headers=auth).json()


# --------------------------- 2. Analytics validation (API) --------------------------- #
def test_analytics_shape(client, auth):
    r = client.get("/applications/analytics", headers=auth)
    assert r.status_code == 200
    a = r.json()
    assert a["total"] == sum(p["count"] for p in a["by_state"])
    assert {p["state"] for p in a["by_state"]} == set(ALL_APP_STATES)
    for rate in ("submit_rate", "interview_rate", "offer_rate", "acceptance_rate"):
        assert 0.0 <= a[rate] <= 100.0


def test_metrics_expose_application_counters(client, auth):
    text = client.get("/metrics", headers=auth).text
    for counter in ("applications_created", "applications_submitted", "interviews", "offers", "rejections"):
        assert counter in text


def test_transition_flow_and_timeline(client, auth):
    app = _approved_application(client, auth)
    if app is None:
        return
    app_id = app["id"]
    # NOT_STARTED -> OFFER is illegal.
    bad = client.post(f"/applications/{app_id}/transition", headers=auth, json={"new_state": "OFFER"})
    assert bad.status_code == 409

    # Walk a legal path as far as the current state allows.
    start = app["status"]
    path = {
        "READY": ["SUBMITTED", "INTERVIEW", "OFFER", "ACCEPTED"],
        "NOT_STARTED": ["READY", "SUBMITTED", "INTERVIEW", "OFFER", "ACCEPTED"],
    }.get(start, [])
    for nxt in path:
        r = client.post(f"/applications/{app_id}/transition", headers=auth, json={"new_state": nxt})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == nxt

    tl = client.get(f"/applications/{app_id}/timeline", headers=auth)
    assert tl.status_code == 200
    assert isinstance(tl.json(), list)


# --------------------------- 3. Material linkage validation (API) --------------------------- #
def test_material_linkage(client, auth):
    app = _approved_application(client, auth)
    if app is None:
        return
    # When materials were generated, the application links them and exposes docs.
    if app["material_id"]:
        assert app["status"] in {"READY", "IN_PROGRESS", "SUBMITTED", "INTERVIEW", "ASSESSMENT", "OFFER", "ACCEPTED", "REJECTED", "WITHDRAWN"}
        assert len(app["documents"]) >= 1
        for d in app["documents"]:
            assert d["material_id"] == app["material_id"]
            assert d["fmt"] in {"txt", "docx", "pdf"}
    else:
        # No profile/materials yet -> application provisioned but not advanced.
        assert app["status"] == "NOT_STARTED"
        assert app["documents"] == []
