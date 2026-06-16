"""Weighted match-scoring engine (rule-based MVP).

score = 0.40*freshers + 0.30*skills + 0.10*location + 0.20*role  (each 0-100)

Classification:
  >= 90  AUTO_APPROVE_ELIGIBLE
  >= 70  REVIEW_QUEUE
  <  70  REJECT

This module is the seam where an AI provider can later replace the heuristics
without changing the pipeline or API.
"""
from dataclasses import dataclass

from ..connectors.base import NormalizedJob
from ..constants import (
    ACCEPT_ROLE_KEYWORDS,
    CLASS_AUTO,
    CLASS_REJECT,
    CLASS_REVIEW,
    FRESHER_KEYWORDS,
    REJECT_TITLE_KEYWORDS,
    REMOTE_INDIA_HINTS,
    ROLE_TO_CATEGORY,
    TARGET_CITIES,
    THRESHOLD_AUTO_APPROVE,
    THRESHOLD_REVIEW,
    WEIGHT_FRESHERS,
    WEIGHT_LOCATION,
    WEIGHT_ROLE,
    WEIGHT_SKILLS,
)
from .filters import max_required_years


@dataclass
class ScoreResult:
    freshers_score: int
    skills_score: int
    location_score: int
    role_score: int
    total_score: int
    classification: str
    matched_resume_category: str | None
    reasoning: str


def _freshers_score(text: str) -> int:
    if any(kw in text for kw in FRESHER_KEYWORDS):
        return 100
    years = max_required_years(text)
    if years is None:
        return 60  # unstated experience — neutral-positive for a fresher
    return 100 if years <= 1 else 0


def _skills_score(text: str, candidate_skills: list[str]) -> int:
    matched = [s for s in candidate_skills if s.lower() in text]
    return min(100, len(matched) * 15)


def _location_score(location: str | None) -> int:
    if not location:
        return 50
    loc = location.lower()
    if any(city in loc for city in TARGET_CITIES):
        return 100
    if any(hint in loc for hint in REMOTE_INDIA_HINTS):
        return 90
    return 20


def _role_score(title: str) -> int:
    t = title.lower()
    if any(kw in t for kw in REJECT_TITLE_KEYWORDS):
        return 0
    if any(kw in t for kw in ACCEPT_ROLE_KEYWORDS):
        return 100
    return 50


def _match_category(title: str) -> str | None:
    t = title.lower()
    for kw, category in ROLE_TO_CATEGORY:
        if kw in t:
            return category
    return None


def _classify(total: int) -> str:
    if total >= THRESHOLD_AUTO_APPROVE:
        return CLASS_AUTO
    if total >= THRESHOLD_REVIEW:
        return CLASS_REVIEW
    return CLASS_REJECT


def score_job(job: NormalizedJob, candidate_skills: list[str]) -> ScoreResult:
    text = f"{job.title} {job.description or ''}".lower()

    fresh = _freshers_score(text)
    skills = _skills_score(text, candidate_skills)
    location = _location_score(job.location)
    role = _role_score(job.title or "")

    total = round(
        WEIGHT_FRESHERS * fresh / 100
        + WEIGHT_SKILLS * skills / 100
        + WEIGHT_LOCATION * location / 100
        + WEIGHT_ROLE * role / 100
    )
    classification = _classify(total)
    reasoning = (
        f"freshers={fresh}, skills={skills}, location={location}, role={role} "
        f"=> total={total} ({classification})"
    )
    return ScoreResult(
        freshers_score=fresh,
        skills_score=skills,
        location_score=location,
        role_score=role,
        total_score=total,
        classification=classification,
        matched_resume_category=_match_category(job.title or ""),
        reasoning=reasoning,
    )
