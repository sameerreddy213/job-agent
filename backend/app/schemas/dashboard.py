from datetime import datetime

from pydantic import BaseModel

from .source import RunHealthOut


class DashboardSummary(BaseModel):
    total_jobs: int
    new_today: int
    auto_eligible: int
    review_queue: int
    rejected: int
    archived: int
    last_run: datetime | None = None
    sources: list[RunHealthOut] = []


class CountPoint(BaseModel):
    label: str
    count: int


class DayPoint(BaseModel):
    day: str
    count: int


class ResumeStat(BaseModel):
    category: str
    matched_jobs: int
    applied: int = 0
    interviews: int = 0
    success_rate: float = 0.0


class AnalyticsOverview(BaseModel):
    jobs_per_day: list[DayPoint]
    applications_per_day: list[DayPoint]
    top_companies: list[CountPoint]
    top_locations: list[CountPoint]
    top_skills: list[CountPoint]
    resume_stats: list[ResumeStat]
    interview_conversion_rate: float
    note: str | None = None
