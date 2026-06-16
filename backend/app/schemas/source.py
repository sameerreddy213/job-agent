from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: str
    apply_policy: str
    enabled: bool
    config: dict
    last_run: datetime | None = None
    last_status: str | None = None
    last_error: str | None = None


class SourceUpdate(BaseModel):
    enabled: bool | None = None
    apply_policy: str | None = None
    config: dict | None = None


class RunHealthOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    run_at: datetime
    jobs_found: int
    new_jobs: int
    errors: int
    response_time_ms: int
    status: str
    detail: str | None = None
