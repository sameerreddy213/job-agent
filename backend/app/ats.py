"""ATS (Applicant Tracking System) detection + application-readiness engine.

Phase 8B. This layer only *understands* where an application would be submitted
and whether the materials are complete. It NEVER submits anything, drives a
browser, or uses Playwright — detection is pure string analysis of the apply URL.
"""
from dataclasses import dataclass, field
from urllib.parse import urlparse


class AtsType:
    GREENHOUSE = "GREENHOUSE"
    LEVER = "LEVER"
    ASHBY = "ASHBY"
    WORKDAY = "WORKDAY"
    SMARTRECRUITERS = "SMARTRECRUITERS"
    JOBVITE = "JOBVITE"
    BAMBOOHR = "BAMBOOHR"
    CUSTOM = "CUSTOM"      # a real apply URL on an unrecognised host
    UNKNOWN = "UNKNOWN"    # no apply URL at all


ALL_ATS_TYPES = {
    AtsType.GREENHOUSE, AtsType.LEVER, AtsType.ASHBY, AtsType.WORKDAY,
    AtsType.SMARTRECRUITERS, AtsType.JOBVITE, AtsType.BAMBOOHR,
    AtsType.CUSTOM, AtsType.UNKNOWN,
}

# Host substrings -> ATS type. Checked in order; first match wins.
_HOST_SIGNATURES: list[tuple[str, str]] = [
    ("greenhouse.io", AtsType.GREENHOUSE),
    ("lever.co", AtsType.LEVER),
    ("ashbyhq.com", AtsType.ASHBY),
    ("myworkdayjobs.com", AtsType.WORKDAY),
    ("workday.com", AtsType.WORKDAY),
    ("smartrecruiters.com", AtsType.SMARTRECRUITERS),
    ("jobvite.com", AtsType.JOBVITE),
    ("bamboohr.com", AtsType.BAMBOOHR),
]

# Fallback when the URL is missing but the discovery source is known.
_SOURCE_SIGNATURES = {
    "greenhouse": AtsType.GREENHOUSE,
    "lever": AtsType.LEVER,
    "ashby": AtsType.ASHBY,
}

# Per-ATS capability table. "Easy apply" = a public form we could realistically
# pre-fill; "manual fields" = the portal needs an account / bespoke questions and
# therefore always needs a human. (We still never auto-submit either way.)
_CAPABILITIES: dict[str, tuple[bool, bool]] = {
    # ats_type: (supports_easy_apply, requires_manual_fields)
    AtsType.GREENHOUSE: (True, False),
    AtsType.LEVER: (True, False),
    AtsType.ASHBY: (True, False),
    AtsType.SMARTRECRUITERS: (True, False),
    AtsType.WORKDAY: (False, True),
    AtsType.JOBVITE: (False, True),
    AtsType.BAMBOOHR: (False, True),
    AtsType.CUSTOM: (False, True),
    AtsType.UNKNOWN: (False, True),
}


@dataclass
class AtsDetection:
    ats_type: str
    ats_version: str | None
    application_url: str | None
    supports_easy_apply: bool
    requires_manual_fields: bool


def _workday_version(host: str) -> str | None:
    """Workday tenants live on wd1/wd2/wd3… subdomains — surface that as version."""
    for part in host.split("."):
        if len(part) == 3 and part.startswith("wd") and part[2].isdigit():
            return part
    return None


def detect_ats(apply_url: str | None, source: str | None = None) -> AtsDetection:
    ats_type = AtsType.UNKNOWN
    version: str | None = None

    host = ""
    if apply_url:
        host = (urlparse(apply_url).hostname or "").lower()

    if host:
        for sig, kind in _HOST_SIGNATURES:
            if sig in host:
                ats_type = kind
                break
        else:
            ats_type = AtsType.CUSTOM  # URL present, host unrecognised
        if ats_type == AtsType.WORKDAY:
            version = _workday_version(host)
    elif source and source.lower() in _SOURCE_SIGNATURES:
        ats_type = _SOURCE_SIGNATURES[source.lower()]

    easy, manual = _CAPABILITIES[ats_type]
    return AtsDetection(
        ats_type=ats_type,
        ats_version=version,
        application_url=apply_url,
        supports_easy_apply=easy,
        requires_manual_fields=manual,
    )


# --------------------------------------------------------------------------- #
# Readiness engine
# --------------------------------------------------------------------------- #
# Score weights — a complete packet sums to 100.
_W_MATERIALS = 40
_W_RESUME = 30
_W_ANSWERS = 30


@dataclass
class ReadinessReport:
    ready_score: int
    ready: bool
    missing_materials: bool
    missing_resume: bool
    missing_answers: bool
    manual_review_required: bool
    reasons: list[str] = field(default_factory=list)


def evaluate_readiness(
    *,
    has_documents: bool,
    resume_category: str | None,
    answer_count: int,
    ats: AtsDetection,
) -> ReadinessReport:
    """Pure readiness calculation from already-loaded application facts."""
    missing_materials = not has_documents
    missing_resume = not resume_category
    missing_answers = answer_count <= 0

    score = 0
    reasons: list[str] = []
    if not missing_materials:
        score += _W_MATERIALS
    else:
        reasons.append("No generated materials packet.")
    if not missing_resume:
        score += _W_RESUME
    else:
        reasons.append("No resume selected/matched.")
    if not missing_answers:
        score += _W_ANSWERS
    else:
        reasons.append("No application answers prepared.")

    manual_review_required = ats.requires_manual_fields
    if manual_review_required:
        reasons.append(f"{ats.ats_type} typically needs manual fields / account.")

    complete = score >= 100
    ready = complete and not manual_review_required
    return ReadinessReport(
        ready_score=score,
        ready=ready,
        missing_materials=missing_materials,
        missing_resume=missing_resume,
        missing_answers=missing_answers,
        manual_review_required=manual_review_required,
        reasons=reasons,
    )
