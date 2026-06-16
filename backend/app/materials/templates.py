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

    # Education line (only the parts that are filled in).
    edu_bits = [b for b in [
        profile.degree, profile.branch, profile.college_name,
        f"CGPA {profile.cgpa}" if profile.cgpa else None,
        f"Graduating {profile.graduation_year}" if profile.graduation_year else None,
    ] if b]
    if edu_bits:
        lines.append("Education: " + " | ".join(edu_bits))

    if profile.languages:
        lines.append(f"Languages: {profile.languages}")
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

    # Identity (so every packet shows the full applicant details).
    add("Full name?", profile.full_name)
    if profile.first_name or profile.last_name:
        name_note = f"First: {profile.first_name or '-'}, Last: {profile.last_name or '-'}"
        if profile.middle_name:
            name_note += f", Middle: {profile.middle_name}"
        # If the first name is two words, suggest splitting the trailing word into
        # the middle name for portals that reject multi-word first names.
        fn = (profile.first_name or "").strip()
        if " " in fn and not profile.middle_name:
            head, _, tail = fn.rpartition(" ")
            name_note += f" (if a two-word first name is rejected, use First: {head}, Middle: {tail})"
        add("First / last name?", name_note)
    add("Date of birth?", profile.date_of_birth)
    add("Gender?", profile.gender)
    add("Nationality?", profile.nationality)

    add("Total years of experience?", "Fresher (0 years)")
    add("Current CTC?", profile.current_ctc or "0 (fresher)")
    add("Expected CTC?", profile.expected_ctc or "Negotiable")
    add("Notice period?", profile.notice_period or "Immediate")
    add("Are you open to relocation?", "Yes" if profile.relocation else "No")
    add("Preferred work location(s)?", profile.preferred_locations)
    add("Willing to work any shift?", profile.shift_preference)
    add("Work authorization?", profile.work_auth)
    add("Languages known?", profile.languages)

    # Contact / address.
    add("Current location?", profile.location)
    address = ", ".join(filter(None, [
        profile.address_line, profile.city, profile.state, profile.pincode,
    ]))
    add("Full address?", address or None)
    add("Email?", profile.email)
    add("College email?", profile.college_email)
    add("Phone?", profile.phone)

    # Education.
    degree_line = " ".join(filter(None, [profile.degree, profile.branch]))
    add("Highest qualification?", profile.qualification)
    add("Degree / branch?", degree_line or None)
    add("College / university?", profile.college_name)
    add("Graduation year?", profile.graduation_year)
    add("CGPA / percentage (graduation)?", profile.cgpa)
    class12 = " | ".join(filter(None, [
        profile.class12_stream, profile.class12_school, profile.class12_board,
        f"{profile.class12_percentage}" if profile.class12_percentage else None,
        f"({profile.class12_year})" if profile.class12_year else None,
    ]))
    add("Class 12 / Intermediate?", class12 or None)
    class10 = " | ".join(filter(None, [
        profile.class10_school, profile.class10_board,
        f"{profile.class10_percentage}" if profile.class10_percentage else None,
        f"({profile.class10_year})" if profile.class10_year else None,
    ]))
    add("Class 10 / SSC?", class10 or None)

    # Links.
    add("LinkedIn profile?", profile.linkedin_url)
    add("GitHub profile?", profile.github_url)
    add("Portfolio?", profile.portfolio_url)
    return answers
