"""Resume Intelligence Layer (Phase 5A) — pure rule engine, no LLM.

Components:
  parser     -> extract plain text from PDF/DOCX/TXT resume files
  skills     -> rule-based skill extraction from text + category profiles
  categorize -> infer the best-fit role category for a resume
  matching   -> recommend the best resume for a job + match/confidence/reasoning
"""
from .categorize import categorize_resume
from .matching import ResumeProfile, RecommendationResult, recommend_resume
from .parser import parse_resume_file
from .skills import extract_skills

__all__ = [
    "parse_resume_file",
    "extract_skills",
    "categorize_resume",
    "recommend_resume",
    "ResumeProfile",
    "RecommendationResult",
]
