"""Optional AI polish layer (WI-3).

When configured (AI_PROVIDER=openrouter + AI_API_KEY), the deterministic,
truthful template output is *rephrased* by an LLM via OpenRouter. The LLM is
strictly instructed never to invent facts. On any failure — disabled, no key,
timeout, HTTP error, empty response — callers fall back to the original
deterministic text, so materials generation never breaks.
"""
from .client import ai_enabled, polish_answer, polish_cover_letter

__all__ = ["ai_enabled", "polish_cover_letter", "polish_answer"]
