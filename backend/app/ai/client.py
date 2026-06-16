"""OpenRouter (OpenAI-compatible) client. Best-effort: returns None on any
problem so the caller keeps the deterministic template."""
import logging

import httpx

from ..config import settings

logger = logging.getLogger("ai")

_GUARDRAIL = (
    "You are an assistant that rephrases job-application text for an entry-level "
    "(fresher) software engineer. STRICT RULES: do not invent or add any skills, "
    "experience, projects, education, employers, dates, or numbers. Only rephrase "
    "what is given for clarity and a professional tone. Keep it concise. Return "
    "only the rewritten text with no preamble, labels, or quotes."
)


def ai_enabled() -> bool:
    return settings.AI_PROVIDER.lower() == "openrouter" and bool(settings.AI_API_KEY)


# Rotates the starting model across calls so load spreads over the free pool.
_rotation = 0


def free_models() -> list[str]:
    """Configured models, restricted to free (":free") slugs only."""
    raw = [m.strip() for m in settings.AI_MODELS.split(",") if m.strip()]
    if settings.AI_MODEL.strip():
        raw.insert(0, settings.AI_MODEL.strip())
    free = [m for m in dict.fromkeys(raw) if m.endswith(":free")]  # dedupe, keep order
    return free


def _call_model(model: str, user_prompt: str) -> str | None:
    """One attempt against a single model. Raises on a retryable HTTP status so
    the caller switches to the next model; returns text or None otherwise."""
    resp = httpx.post(
        f"{settings.AI_BASE_URL.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.AI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": settings.AI_MAX_TOKENS,
            "temperature": 0.4,
            "messages": [
                {"role": "system", "content": _GUARDRAIL},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=settings.AI_TIMEOUT_SECONDS,
    )
    # Rate-limited / quota / unavailable -> signal a switch to the next model.
    if resp.status_code in (402, 408, 409, 429, 500, 502, 503, 504):
        raise RuntimeError(f"{model} unavailable (HTTP {resp.status_code})")
    resp.raise_for_status()
    data = resp.json()
    text = (data.get("choices") or [{}])[0].get("message", {}).get("content")
    return (text or "").strip() or None


def _chat(user_prompt: str) -> str | None:
    """Try each free model in rotation; switch on rate-limit/error. Returns the
    first good completion, or None so the caller keeps the deterministic text."""
    if not ai_enabled():
        return None
    models = free_models()
    if not models:
        logger.warning("AI enabled but no free models configured; using templates")
        return None

    global _rotation
    start = _rotation % len(models)
    _rotation += 1
    for i in range(len(models)):
        model = models[(start + i) % len(models)]
        try:
            text = _call_model(model, user_prompt)
            if text:
                return text
            logger.warning("model %s returned empty; switching", model)
        except Exception as e:  # noqa: BLE001 - try the next free model
            logger.warning("model %s failed (%s); switching", model, e)
    logger.warning("all free models exhausted; using deterministic text")
    return None


def polish_cover_letter(draft: str, company: str | None, title: str | None) -> str | None:
    prompt = (
        f"Rephrase this cover letter for the role '{title or 'the role'}' at "
        f"'{company or 'the company'}'. Preserve every fact, name, link, and the "
        f"sign-off exactly.\n\n---\n{draft}"
    )
    return _chat(prompt)


def polish_answer(question: str, answer: str, company: str | None, title: str | None) -> str | None:
    prompt = (
        f"Improve the wording of this answer to a job-application question. Keep it "
        f"to 2-4 sentences and preserve all facts.\n\n"
        f"Role: {title or '-'} at {company or '-'}\n"
        f"Question: {question}\nAnswer: {answer}"
    )
    return _chat(prompt)
