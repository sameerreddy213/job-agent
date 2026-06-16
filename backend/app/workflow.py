"""Job workflow state machine.

Enforces valid transitions, records every transition to job_state_history AND
the audit log, and keeps the legacy `archived` flag in sync.
"""
from sqlalchemy.orm import Session

from .audit import write_audit
from .models.job import Job
from .models.workflow import JobStateHistory


class State:
    DISCOVERED = "DISCOVERED"
    FILTERED = "FILTERED"
    SCORED = "SCORED"
    REVIEW_QUEUE = "REVIEW_QUEUE"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MATERIALS_GENERATED = "MATERIALS_GENERATED"
    READY_TO_APPLY = "READY_TO_APPLY"
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


ALL_STATES = {
    State.DISCOVERED, State.FILTERED, State.SCORED, State.REVIEW_QUEUE, State.APPROVED,
    State.REJECTED, State.MATERIALS_GENERATED, State.READY_TO_APPLY, State.APPLIED,
    State.FAILED, State.ARCHIVED,
}

VALID_TRANSITIONS: dict[str, set[str]] = {
    State.DISCOVERED: {State.FILTERED, State.SCORED, State.ARCHIVED},
    State.FILTERED: {State.ARCHIVED},
    State.SCORED: {State.REVIEW_QUEUE, State.REJECTED, State.ARCHIVED},
    State.REVIEW_QUEUE: {State.APPROVED, State.REJECTED, State.ARCHIVED},
    State.APPROVED: {State.MATERIALS_GENERATED, State.READY_TO_APPLY, State.REJECTED, State.ARCHIVED},
    State.MATERIALS_GENERATED: {State.READY_TO_APPLY, State.REJECTED, State.ARCHIVED},
    State.READY_TO_APPLY: {State.APPLIED, State.FAILED, State.REJECTED, State.ARCHIVED},
    State.APPLIED: {State.ARCHIVED, State.FAILED},
    State.FAILED: {State.READY_TO_APPLY, State.ARCHIVED},
    State.REJECTED: {State.REVIEW_QUEUE, State.ARCHIVED},
    State.ARCHIVED: set(),
}


class InvalidTransition(Exception):
    pass


def can_transition(current: str, new: str) -> bool:
    return new in VALID_TRANSITIONS.get(current, set())


def _record(db: Session, job: Job, previous: str | None, new: str, actor: str, reason: str | None):
    db.add(
        JobStateHistory(job_id=job.id, previous_state=previous, new_state=new, actor=actor, reason=reason)
    )
    write_audit(
        db, actor, "workflow.transition", "job", job.id,
        {"from": previous, "to": new, "reason": reason}, commit=False,
    )


def transition(
    db: Session, job: Job, new_state: str, actor: str, reason: str | None = None, commit: bool = True
) -> None:
    if new_state not in ALL_STATES:
        raise InvalidTransition(f"Unknown state '{new_state}'")
    current = job.status
    if not can_transition(current, new_state):
        raise InvalidTransition(f"Illegal transition {current} -> {new_state}")

    _record(db, job, current, new_state, actor, reason)
    job.status = new_state
    if new_state == State.ARCHIVED:
        job.archived = True
    if commit:
        db.commit()


def snooze(db: Session, job: Job, until, actor: str, reason: str | None = None, commit: bool = True) -> None:
    """Snooze keeps the job in its current state but records a history entry."""
    job.snoozed_until = until
    _record(db, job, job.status, job.status, actor, reason or "snoozed")
    if commit:
        db.commit()
