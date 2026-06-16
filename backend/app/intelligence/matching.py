"""Job -> Resume recommendation engine (rule-based).

Given a job's text and the set of available resumes (category + detected
skills), pick the best resume and produce match score, matched/missing skills,
a confidence score, and human-readable reasoning. No LLM.
"""
from dataclasses import dataclass, field

from ..constants import ROLE_TO_CATEGORY
from .skills import extract_skills


@dataclass
class ResumeProfile:
    category: str
    skills: set[str] = field(default_factory=set)


@dataclass
class RecommendationResult:
    selected_category: str | None
    match_score: int
    matched_skills: list[str]
    missing_skills: list[str]
    confidence: int
    reasoning: str


def role_from_title(title: str | None) -> str | None:
    t = (title or "").lower()
    for kw, category in ROLE_TO_CATEGORY:
        if kw in t:
            return category
    return None


def _coverage(job_skills: set[str], resume_skills: set[str]) -> float:
    if not job_skills:
        return 0.0
    return len(job_skills & resume_skills) / len(job_skills)


def recommend_resume(
    job_title: str | None, job_text: str | None, resumes: list[ResumeProfile]
) -> RecommendationResult:
    job_skills = set(extract_skills(f"{job_title or ''} {job_text or ''}"))
    role_category = role_from_title(job_title)

    if not resumes:
        return RecommendationResult(
            selected_category=role_category,
            match_score=0,
            matched_skills=[],
            missing_skills=sorted(job_skills),
            confidence=0,
            reasoning="No resumes uploaded yet; selection is by job title only.",
        )

    # Rank resumes by skill coverage, with a small bonus when the resume's
    # category matches the role implied by the job title.
    scored = []
    for r in resumes:
        coverage = _coverage(job_skills, r.skills)
        score = round(coverage * 100)
        role_bonus = 10 if r.category == role_category else 0
        scored.append((min(100, score + role_bonus), score, r))
    scored.sort(key=lambda x: x[0], reverse=True)

    top_total, top_score, top = scored[0]
    second_total = scored[1][0] if len(scored) > 1 else 0
    margin = top_total - second_total

    matched = sorted(job_skills & top.skills)
    missing = sorted(job_skills - top.skills)

    # Confidence: blends absolute match with the lead over the runner-up.
    if not job_skills:
        # No explicit skills in the job; lean on the title-role signal only.
        confidence = 20 if role_category and top.category == role_category else 10
        reasoning = (
            f"No explicit skills detected in the job posting; selected "
            f"'{top.category}'"
            + (" by job-title role match." if top.category == role_category else " as the closest available resume.")
        )
        return RecommendationResult(top.category, 0, [], missing, confidence, reasoning)

    confidence = round(0.7 * top_score + 0.3 * margin)
    if top.category == role_category:
        confidence = min(100, confidence + 10)
    if len(job_skills) < 3:
        confidence = min(confidence, 40)
    confidence = max(0, min(100, confidence))

    runner_up = ""
    if len(scored) > 1:
        runner_up = f" Chosen over '{scored[1][2].category}' ({scored[1][1]}%) by {margin} points."
    reasoning = (
        f"Selected '{top.category}': matches {len(matched)}/{len(job_skills)} "
        f"required skills ({', '.join(matched) or 'none'})."
        + (f" Missing: {', '.join(missing)}." if missing else "")
        + runner_up
    )

    return RecommendationResult(
        selected_category=top.category,
        match_score=top_score,
        matched_skills=matched,
        missing_skills=missing,
        confidence=confidence,
        reasoning=reasoning,
    )
