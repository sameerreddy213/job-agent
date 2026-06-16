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


def _chat(user_prompt: str) -> str | None:
    if not ai_enabled():
        return None
    try:
        resp = httpx.post(
            f"{settings.AI_BASE_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.AI_MODEL,
                "max_tokens": settings.AI_MAX_TOKENS,
                "temperature": 0.4,
                "messages": [
                    {"role": "system", "content": _GUARDRAIL},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=settings.AI_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content")
        text = (text or "").strip()
        return text or None
    except Exception as e:  # noqa: BLE001 - AI is strictly best-effort
        logger.warning("AI polish failed; using deterministic text: %s", e)
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
