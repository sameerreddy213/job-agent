"""Structured JSON logging.

Every log line is a single JSON object with the agreed fields:
  timestamp, level, service, request_id, user, action, status, duration_ms, message
Fields that don't apply to a given record are emitted as null.
"""
import datetime
import json
import logging
import sys

_SERVICE = "api"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.datetime.fromtimestamp(
                record.created, tz=datetime.timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", _SERVICE),
            "request_id": getattr(record, "request_id", None),
            "user": getattr(record, "user", None),
            "action": getattr(record, "action", None),
            "status": getattr(record, "status", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(service: str = "api", level: int = logging.INFO) -> None:
    global _SERVICE
    _SERVICE = service

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Uvicorn access logs are redundant with our request middleware; quiet them.
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False
