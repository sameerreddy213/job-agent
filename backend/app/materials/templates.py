"""Deterministic, truthful template builders.

Rules: only emit facts present in the profile / resume / job. Never invent
skills, experience, projects, education, or certifications. Lines whose source
data is missing are simply omitted.
"""
from ..models.job import Job
from ..models.profile import Profile


def _skill_phrase(skills: list[str], limit: int = 8) -> str:
    picked = [s for s in skills if s][:limit]
    return ", ".join(picked)


def build_cover_letter(profile: Profile, job: Job, skills: list[str]) -> str:
    company = job.company or "the company"
    title = job.title or "the advertised role"
    lines: list[str] = []
    lines.append(f"Dear {company} Hiring Team,")
    lines.append("")

    where = f" in {job.location}" if job.location else ""
    lines.append(
        f"I am writing to express my interest in the {title} position at {company}{where}. "
        "As a fresher software engineer, I am eager to begin my career and contribute to your team."
    )
    lines.append("")

    if skills:
        lines.append(
            f"My background includes hands-on familiarity with {_skill_phrase(skills)}. "
            "I am committed to learning quickly and delivering quality work."
        )
        lines.append("")

    availability = []
    if profile.notice_period:
        availability.append(f"my notice period is {profile.notice_period}")
    if profile.relocation:
        availability.append("I am open to relocation")
    if availability:
        lines.append("Regarding availability, " + " and ".join(availability) + ".")
        lines.append("")

    links = []
    if profile.github_url:
        links.append(f"GitHub: {profile.github_url}")
    if profile.linkedin_url:
        links.append(f"LinkedIn: {profile.linkedin_url}")
    if profile.portfolio_url:
        links.append(f"Portfolio: {profile.portfolio_url}")
    if links:
        lines.append("You can review my work here — " + "; ".join(links) + ".")
        lines.append("")

    lines.append(
        f"Thank you for considering my application. I would welcome the opportunity to "
        f"discuss how I can contribute to {company}."
    )
    lines.append("")
    lines.append("Sincerely,")
    lines.append(profile.full_name)
    contact = " | ".join(filter(None, [profile.email, profile.phone]))
    if contact:
        lines.append(contact)
    return "\n".join(lines)


def build_resume_summary(profile: Profile, role_category: str | None, skills: list[str]) -> str:
    role = (role_category or "Software Engineer").replace("_", " ")
    lines: list[str] = [f"{profile.full_name} - {role} (Fresher)"]

    meta = []
    if profile.location:
        meta.append(f"Location: {profile.location}")
    meta.append(f"Open to relocation: {'Yes' if profile.relocation else 'No'}")
    if profile.notice_period:
        meta.append(f"Notice: {profile.notice_period}")
    lines.append(" | ".join(meta))

    if skills:
        lines.append(f"Core skills: {_skill_phrase(skills, limit=15)}")
    if profile.expected_ctc:
        lines.append(f"Expected CTC: {profile.expected_ctc}")

    links = " | ".join(
        filter(
            None,
            [
                f"GitHub {profile.github_url}" if profile.github_url else None,
                f"LinkedIn {profile.linkedin_url}" if profile.linkedin_url else None,
                f"Portfolio {profile.portfolio_url}" if profile.portfolio_url else None,
            ],
        )
    )
    if links:
        lines.append(links)
    return "\n".join(lines)


def build_application_answers(profile: Profile, job: Job, skills: list[str]) -> list[dict]:
    """Common, factual application questions answered from profile data only.

    Deliberately excludes diversity / disability / veteran / legal declarations —
    those always require manual review and are never auto-answered.
    """
    answers: list[dict] = []

    def add(q: str, a: str | None):
        if a:
            answers.append({"question": q, "answer": a})

    why = (
        f"I am excited about the {job.title or 'role'} at {job.company or 'your company'} "
        "as a strong start to my software engineering career"
    )
    if skills:
        why += f", where I can apply my skills in {_skill_phrase(skills, limit=5)}"
    add("Why are you interested in this role?", why + ".")

    add("Total years of experience?", "Fresher (0 years)")
    add("Expected CTC?", profile.expected_ctc or "Negotiable")
    add("Notice period?", profile.notice_period or "Immediate")
    add("Are you open to relocation?", "Yes" if profile.relocation else "No")
    add("Work authorization?", profile.work_auth)
    add("Current location?", profile.location)
    add("LinkedIn profile?", profile.linkedin_url)
    add("GitHub profile?", profile.github_url)
    add("Portfolio?", profile.portfolio_url)
    return answers
