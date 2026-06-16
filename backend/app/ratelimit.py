"""Minimal in-process login rate limiter (sliding window per key).

Single-instance deployment, so an in-memory window is sufficient. If the app is
ever scaled out, replace this with a shared store (e.g. Redis).
"""
import time
from collections import defaultdict, deque

from .config import settings

_attempts: dict[str, deque] = defaultdict(deque)


def _prune(key: str, now: float) -> None:
    window = settings.LOGIN_WINDOW_SECONDS
    dq = _attempts[key]
    while dq and now - dq[0] > window:
        dq.popleft()


def is_locked(key: str) -> bool:
    now = time.monotonic()
    _prune(key, now)
    return len(_attempts[key]) >= settings.LOGIN_MAX_ATTEMPTS


def record_failure(key: str) -> None:
    now = time.monotonic()
    _prune(key, now)
    _attempts[key].append(now)


def reset(key: str) -> None:
    _attempts.pop(key, None)
