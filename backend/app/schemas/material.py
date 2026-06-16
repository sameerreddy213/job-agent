import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnswerItem(BaseModel):
    question: str
    answer: str


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    resume_category: str | None = None
    cover_letter_required: bool
    cover_letter_text: str | None = None
    resume_summary_text: str | None = None
    application_answers: list[AnswerItem] = []
    generated_at: datetime
    # Convenience flags for the dashboard (which export formats exist).
    formats: list[str] = []
