"""Phase 7B — workflow completion validation.

Three required verification areas:
  1. Transition matrix validation  (pure unit, no server)
  2. Bulk action validation        (API, running stack)
  3. Workflow metrics validation   (API, running stack)
"""
from app.workflow import ALL_STATES, State, VALID_TRANSITIONS, can_transition


# --------------------------- 1. Transition matrix --------------------------- #
def test_matrix_only_references_known_states():
    """Every source and target in the matrix is a declared state."""
    for src, targets in VALID_TRANSITIONS.items():
        assert src in ALL_STATES, f"unknown source state {src}"
        for dst in targets:
            assert dst in ALL_STATES, f"unknown target state {dst}"


def test_matrix_is_total():
    """Every state has an (possibly empty) entry in the matrix."""
    assert set(VALID_TRANSITIONS.keys()) == ALL_STATES


def test_matrix_has_no_self_loops():
    """A real transition never targets its own state (self == snooze, handled separately)."""
    for src, targets in VALID_TRANSITIONS.items():
        assert src not in targets, f"{src} illegally transitions to itself"


def test_archived_is_terminal():
    assert VALID_TRANSITIONS[State.ARCHIVED] == set()


def test_every_state_reaches_archived():
    """ARCHIVED is the universal sink: reachable (directly or transitively) from all."""
    for state in ALL_STATES:
        if state == State.ARCHIVED:
            continue
        seen, stack = set(), [state]
        while stack:
            cur = stack.pop()
            for nxt in VALID_TRANSITIONS[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        assert State.ARCHIVED in seen, f"{state} cannot reach ARCHIVED"


def test_representative_valid_and_invalid():
    # valid
    assert can_transition(State.SCORED, State.REVIEW_QUEUE)
    assert can_transition(State.REVIEW_QUEUE, State.APPROVED)
    assert can_transition(State.APPROVED, State.MATERIALS_GENERATED)
    assert can_transition(State.READY_TO_APPLY, State.APPLIED)
    # invalid
    assert not can_transition(State.DISCOVERED, State.APPLIED)
    assert not can_transition(State.FILTERED, State.APPROVED)
    assert not can_transition(State.APPLIED, State.APPROVED)
    assert not can_transition("NONSENSE", State.APPROVED)


# --------------------------- 2. Bulk action validation --------------------------- #
def test_bulk_approve_reports_per_id_results(client, auth):
    jobs = client.get("/queue", headers=auth, params={"limit": 5}).json()
    ids = [j["id"] for j in jobs]
    if not ids:
        return
    r = client.post("/jobs/bulk/approve", headers=auth, json={"ids": ids})
    assert r.status_code == 200
    body = r.json()
    assert body["requested"] == len(ids)
    assert body["succeeded"] + body["failed"] == len(ids)
    assert len(body["results"]) == len(ids)

    # Re-approving the same ids is now illegal (APPROVED -> APPROVED): all fail.
    again = client.post("/jobs/bulk/approve", headers=auth, json={"ids": ids})
    assert again.status_code == 200
    assert again.json()["succeeded"] == 0


def test_bulk_handles_unknown_ids(client, auth):
    bogus = "00000000-0000-0000-0000-000000000000"
    r = client.post("/jobs/bulk/archive", headers=auth, json={"ids": [bogus]})
    assert r.status_code == 200
    body = r.json()
    assert body["failed"] == 1
    assert body["results"][0]["ok"] is False


# --------------------------- 3. Workflow metrics validation --------------------------- #
def test_analytics_shape_and_consistency(client, auth):
    r = client.get("/workflow/analytics", headers=auth, params={"days": 30})
    assert r.status_code == 200
    a = r.json()
    # decisions == approvals + rejections + snoozes
    assert a["decisions"] == a["approvals"] + a["rejections"] + a["snoozes"]
    # percentages within range and (approximately) sum to 100 when there are decisions
    for k in ("approval_pct", "rejection_pct", "snooze_pct"):
        assert 0.0 <= a[k] <= 100.0
    if a["decisions"] > 0:
        assert abs(a["approval_pct"] + a["rejection_pct"] + a["snooze_pct"] - 100.0) < 0.5
    # jobs_by_state covers every declared state
    states = {p["state"] for p in a["jobs_by_state"]}
    assert states == set(ALL_STATES)


def test_approval_stats_rates(client, auth):
    r = client.get("/workflow/approval-stats", headers=auth, params={"days": 30})
    assert r.status_code == 200
    s = r.json()
    decided = s["approved"] + s["rejected"]
    if decided > 0:
        assert abs(s["approval_rate"] + s["rejection_rate"] - 100.0) < 0.5
    else:
        assert s["approval_rate"] == 0.0 and s["rejection_rate"] == 0.0


def test_metrics_endpoint_exposes_workflow_counters(client, auth):
    r = client.get("/metrics", headers=auth)
    assert r.status_code == 200
    text = r.text
    for counter in (
        "workflow_transitions",
        "workflow_failures",
        "jobs_approved",
        "jobs_rejected",
        "jobs_archived",
    ):
        assert counter in text


def test_timeline_returns_events(client, auth):
    r = client.get("/workflow/timeline", headers=auth, params={"limit": 10})
    assert r.status_code == 200
    events = r.json()
    assert isinstance(events, list)
    if events:
        e = events[0]
        assert {"job_id", "new_state", "actor", "created_at"} <= e.keys()
