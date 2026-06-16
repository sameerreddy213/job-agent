"""Request-logging middleware: emits one structured JSON line per request with
request_id, user (best-effort from the bearer token), action, status, duration_ms.
"""
import logging
import time
import uuid

from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .security import decode_token

logger = logging.getLogger("request")


def _extract_user(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1]
    try:
        return decode_token(token).get("sub")
    except (JWTError, Exception):
        return None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            logger.info(
                f"{request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "user": _extract_user(request),
                    "action": f"{request.method} {request.url.path}",
                    "status": status,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                },
            )
