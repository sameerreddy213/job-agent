"""Telegram Bot API client: sendMessage + getUpdates with retry + rate limiting."""
import threading
import time

import httpx

from ..config import settings

_API = "https://api.telegram.org/bot{token}/{method}"
_MIN_INTERVAL = 1.0  # seconds between sends (Telegram per-chat limit ~1/s)
_lock = threading.Lock()
_last_send = 0.0


def token_configured() -> bool:
    return bool(settings.TELEGRAM_BOT_TOKEN)


def _url(method: str) -> str:
    return _API.format(token=settings.TELEGRAM_BOT_TOKEN, method=method)


def _rate_limit() -> None:
    global _last_send
    with _lock:
        wait = _MIN_INTERVAL - (time.monotonic() - _last_send)
        if wait > 0:
            time.sleep(wait)
        _last_send = time.monotonic()


def send_message(text: str, chat_id: str, attempts: int = 3) -> tuple[bool, int, str | None]:
    """Returns (ok, retries, error). Honors 429 retry_after; backs off on errors."""
    if not token_configured() or not chat_id:
        return False, 0, "not configured"

    error: str | None = None
    for i in range(attempts):
        _rate_limit()
        try:
            resp = httpx.post(
                _url("sendMessage"),
                json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
                timeout=settings.HTTP_TIMEOUT_SECONDS,
            )
            if resp.status_code == 200:
                return True, i, None
            if resp.status_code == 429:
                retry_after = resp.json().get("parameters", {}).get("retry_after", 2 ** i)
                time.sleep(min(retry_after, 30))
                error = "rate limited"
                continue
            error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:  # noqa: BLE001
            error = str(e)[:200]
        time.sleep(2 ** i)
    return False, attempts - 1, error


def get_updates(offset: int | None, timeout: int = 0) -> list[dict]:
    if not token_configured():
        return []
    params: dict = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    resp = httpx.get(_url("getUpdates"), params=params, timeout=settings.HTTP_TIMEOUT_SECONDS + timeout)
    resp.raise_for_status()
    return resp.json().get("result", [])
