"""Long-poll getUpdates and dispatch commands. Offset persisted in DB."""
import logging

from sqlalchemy.orm import Session

from ..audit import write_audit
from . import client
from .commands import handle_update
from .notifier import get_settings

logger = logging.getLogger("worker")


def poll_once(db: Session) -> int:
    """Fetch and handle pending updates. Returns the number handled."""
    if not client.token_configured():
        return 0
    s = get_settings(db)
    offset = (s.last_update_id + 1) if s.last_update_id is not None else None
    try:
        updates = client.get_updates(offset)
    except Exception:  # noqa: BLE001
        logger.exception("telegram getUpdates failed", extra={"service": "worker", "action": "telegram.poll"})
        return 0

    handled = 0
    max_id = s.last_update_id or 0
    for upd in updates:
        uid = upd.get("update_id", 0)
        max_id = max(max_id, uid)
        try:
            cmd = handle_update(db, upd)
            if cmd:
                handled += 1
                write_audit(db, "telegram", "telegram.command", "telegram", payload={"command": cmd}, commit=False)
        except Exception:  # noqa: BLE001
            logger.exception("telegram command failed", extra={"service": "worker", "action": "telegram.command"})

    if updates:
        s.last_update_id = max_id
        db.commit()
    return handled
