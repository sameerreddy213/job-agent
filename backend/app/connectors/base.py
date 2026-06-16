"""Connector interface + shared data types.

Every source connector implements BaseConnector:
  - discover_jobs()  -> list of raw provider payloads
  - normalize_job()  -> map a raw payload to NormalizedJob
  - health_check()   -> lightweight reachability/credential check
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NormalizedJob:
    job_id: str
    source: str
    company: str
    title: str
    location: str | None = None
    description: str | None = None
    experience: str | None = None
    apply_url: str | None = None
    posted_date: datetime | None = None
    employment_type: str | None = None
    remote_status: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class HealthResult:
    ok: bool
    detail: str = ""


class BaseConnector(ABC):
    """Abstract source connector. `source` is the stored Source.name."""

    source: str = "base"

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    @abstractmethod
    def discover_jobs(self) -> list[dict]:
        """Return raw provider job payloads."""

    @abstractmethod
    def normalize_job(self, raw: dict) -> NormalizedJob:
        """Map a single raw payload to the normalized schema."""

    @abstractmethod
    def health_check(self) -> HealthResult:
        """Cheap check that the source is reachable / configured."""

    def collect(self) -> list[NormalizedJob]:
        """Discover + normalize, skipping payloads that fail to map."""
        out: list[NormalizedJob] = []
        for raw in self.discover_jobs():
            try:
                out.append(self.normalize_job(raw))
            except Exception:
                # A single malformed posting must not abort the whole source.
                continue
        return out
