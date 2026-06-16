"""Infer the best-fit role category for a resume from its detected skills."""
from .skills import CATEGORY_PROFILES, extract_skills


def categorize_resume(text: str | None, skills: list[str] | None = None) -> tuple[str | None, int]:
    """Return (category, confidence 0-100) based on overlap with category profiles.

    If `skills` is provided it's used directly; otherwise skills are extracted
    from `text`.
    """
    detected = set(skills if skills is not None else extract_skills(text))
    if not detected:
        return None, 0

    best_category: str | None = None
    best_ratio = 0.0
    for category, profile in CATEGORY_PROFILES.items():
        if not profile:
            continue
        overlap = len(detected & profile) / len(profile)
        if overlap > best_ratio:
            best_ratio = overlap
            best_category = category

    return best_category, round(best_ratio * 100)
