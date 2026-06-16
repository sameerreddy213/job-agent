"""Materials Generation Engine (Phase 6A) — deterministic templates, no LLM.

Generates cover letters, resume summaries, and application answers strictly from
verified profile + resume data. Never invents skills, experience, projects,
education, or certifications. Exports to TXT / DOCX / PDF.
"""
from .generator import GenerationError, generate_materials

__all__ = ["generate_materials", "GenerationError"]
