"""Orchestrates material generation: build texts -> write files -> upsert row."""
import os

from sqlalchemy.orm import Session

from ..ai import ai_enabled, polish_answer, polish_cover_letter
from ..config import settings
from ..intelligence import extract_skills
from ..models.job import Job
from ..models.material import Material
from ..models.profile import Profile
from ..models.resume import ResumeVersion
from .exporters import write_docx, write_pdf, write_txt
from .templates import build_application_answers, build_cover_letter, build_resume_summary


class GenerationError(Exception):
    """Raised when materials cannot be generated (e.g. profile not set)."""


def _resume_skills(db: Session, category: str | None) -> list[str]:
    if not category:
        return []
    version = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.role_category == category, ResumeVersion.is_current.is_(True))
        .first()
    )
    return [s for s in (version.skills_detected if version else []) if isinstance(s, str)]


def generate_materials(
    db: Session,
    job: Job,
    cover_letter: bool = True,
    category_override: str | None = None,
) -> Material:
    profile = db.get(Profile, 1)
    if profile is None:
        raise GenerationError("Profile is not set; cannot generate materials.")

    category = category_override or (job.score.matched_resume_category if job.score else None)

    # Emphasis skills: prefer the job∩resume matched skills, else the resume's
    # own detected skills, else skills found in the job text. Never invented.
    resume_skills = _resume_skills(db, category)
    matched = list(job.score.matched_skills) if (job.score and job.score.matched_skills) else []
    if matched:
        skills = matched
    elif resume_skills:
        job_skills = set(extract_skills(f"{job.title} {job.description or ''}"))
        skills = sorted(set(resume_skills) & job_skills) or resume_skills
    else:
        skills = []

    cover_text = build_cover_letter(profile, job, skills) if cover_letter else None
    summary_text = build_resume_summary(profile, category, skills)
    answers = build_application_answers(profile, job, skills)

    # Optional AI polish (WI-3). No-op unless AI_PROVIDER=openrouter + key set;
    # any failure leaves the deterministic text untouched.
    if ai_enabled():
        if cover_text:
            improved = polish_cover_letter(cover_text, job.company, job.title)
            if improved:
                cover_text = improved
        # Only the open-ended narrative answer is rephrased; factual answers
        # (CTC, dates, education, links, etc.) stay verbatim.
        for qa in answers:
            if qa.get("question") == "Why are you interested in this role?":
                improved_ans = polish_answer(qa["question"], qa.get("answer", ""), job.company, job.title)
                if improved_ans:
                    qa["answer"] = improved_ans
                break

    sections: list[tuple[str, str]] = []
    if cover_text:
        sections.append(("Cover Letter", cover_text))
    sections.append(("Resume Summary", summary_text))
    answers_body = "\n\n".join(f"Q: {a['question']}\nA: {a['answer']}" for a in answers)
    sections.append(("Application Answers", answers_body))

    out_dir = os.path.join(settings.GENERATED_DIR, str(job.id))
    os.makedirs(out_dir, exist_ok=True)
    txt_path = os.path.join(out_dir, "packet.txt")
    docx_path = os.path.join(out_dir, "packet.docx")
    pdf_path = os.path.join(out_dir, "packet.pdf")
    write_txt(txt_path, sections)
    write_docx(docx_path, sections)
    write_pdf(pdf_path, sections)

    material = db.query(Material).filter(Material.job_id == job.id).first()
    if material is None:
        material = Material(job_id=job.id)
        db.add(material)
    material.resume_category = category
    material.cover_letter_required = cover_letter
    material.cover_letter_text = cover_text
    material.resume_summary_text = summary_text
    material.application_answers = answers
    material.txt_path = txt_path
    material.docx_path = docx_path
    material.pdf_path = pdf_path
    db.commit()
    db.refresh(material)
    return material
