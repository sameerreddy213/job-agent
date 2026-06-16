"""Manual-apply packet builder (Phase 8C).

Assembles a self-contained application packet (Resume + Cover Letter +
Application Answers + Application Notes) into TXT/DOCX/PDF so the user can apply
*manually*. This module writes files only — it never submits anything.
"""
import os
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .config import settings
from .materials.exporters import write_docx, write_pdf, write_txt
from .models.application import Application
from .models.job import Job
from .models.material import Material


class PacketError(Exception):
    """Raised when a packet cannot be built (e.g. materials not generated)."""


def build_sections(app: Application, material: Material, job: Job | None) -> list[tuple[str, str]]:
    """The ordered packet contents. Notes are appended so the user has their own
    reminders in the same document."""
    sections: list[tuple[str, str]] = []
    header = []
    if job:
        header.append(f"{job.title} — {job.company}")
    if app.application_url:
        header.append(f"Apply at: {app.application_url}")
    if header:
        sections.append(("Application", "\n".join(header)))

    if material.cover_letter_text:
        sections.append(("Cover Letter", material.cover_letter_text))
    if material.resume_summary_text:
        sections.append(("Resume", material.resume_summary_text))

    answers = material.application_answers or []
    if answers:
        body = "\n\n".join(
            f"Q: {a.get('question', '')}\nA: {a.get('answer', '')}"
            for a in answers if isinstance(a, dict)
        )
        sections.append(("Application Answers", body))

    sections.append(("Application Notes", app.notes or "(none)"))
    return sections


def generate_packet(db: Session, app: Application, material: Material, job: Job | None, commit: bool = True) -> Application:
    if material is None:
        raise PacketError("Materials must be generated before building a packet.")
    sections = build_sections(app, material, job)

    out_dir = os.path.join(settings.GENERATED_DIR, str(app.job_id), "packet")
    os.makedirs(out_dir, exist_ok=True)
    txt_path = os.path.join(out_dir, "application_packet.txt")
    docx_path = os.path.join(out_dir, "application_packet.docx")
    pdf_path = os.path.join(out_dir, "application_packet.pdf")
    write_txt(txt_path, sections)
    write_docx(docx_path, sections)
    write_pdf(pdf_path, sections)

    app.packet_txt_path = txt_path
    app.packet_docx_path = docx_path
    app.packet_pdf_path = pdf_path
    app.packet_generated_at = datetime.now(timezone.utc)
    if commit:
        db.commit()
        db.refresh(app)
    return app
