"""Fresher filtering + blacklists.

Rejects: blacklisted companies, blacklisted keywords, senior titles, and
>1-year experience requirements.
"""
from dataclasses import dataclass, field

from ..connectors.base import NormalizedJob
from ..constants import (
    EXPERIENCE_REQ_REGEX,
    MAX_FRESHER_YEARS,
    REJECT_TITLE_KEYWORDS,
)


@dataclass
class Blacklists:
    companies: set[str] = field(default_factory=set)  # lowercased company names
    # (keyword_lower, applies_to) where applies_to in {title, description, both}
    keywords: list[tuple[str, str]] = field(default_factory=list)


def max_required_years(text: str | None) -> int | None:
    if not text:
        return None
    years = [int(m.group(1)) for m in EXPERIENCE_REQ_REGEX.finditer(text)]
    return max(years) if years else None


def filter_job(job: NormalizedJob, blacklists: Blacklists | None = None) -> tuple[bool, str]:
    """Return (passed, reason)."""
    blacklists = blacklists or Blacklists()
    title = (job.title or "").lower()
    description = (job.description or "").lower()

    if (job.company or "").lower() in blacklists.companies:
        return False, f"rejected: company '{job.company}' is blacklisted"

    for kw, applies_to in blacklists.keywords:
        in_title = kw in title
        in_desc = kw in description
        if (
            (applies_to == "title" and in_title)
            or (applies_to == "description" and in_desc)
            or (applies_to == "both" and (in_title or in_desc))
        ):
            return False, f"rejected: blacklisted keyword '{kw}'"

    for kw in REJECT_TITLE_KEYWORDS:
        if kw in title:
            return False, f"rejected: title contains '{kw.strip()}'"

    years = max_required_years(f"{job.title} {job.description or ''}")
    if years is not None and years > MAX_FRESHER_YEARS:
        return False, f"rejected: requires {years}+ years experience"

    return True, "passed fresher filter"
