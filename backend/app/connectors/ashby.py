"""Ashby public job-board API connector.

Endpoint: https://api.ashbyhq.com/posting-api/job-board/{board}
Config:   {"boards": ["openai", "..."]}
"""
from datetime import datetime

import httpx

from ..config import settings
from .base import BaseConnector, HealthResult, NormalizedJob

BASE = "https://api.ashbyhq.com/posting-api/job-board"


class AshbyConnector(BaseConnector):
    source = "ashby"

    def _boards(self) -> list[str]:
        return self.config.get("boards", [])

    def discover_jobs(self) -> list[dict]:
        jobs: list[dict] = []
        with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
            for board in self._boards():
                resp = client.get(f"{BASE}/{board}")
                resp.raise_for_status()
                for j in resp.json().get("jobs", []):
                    j["_board"] = board
                    jobs.append(j)
        return jobs

    def normalize_job(self, raw: dict) -> NormalizedJob:
        posted = raw.get("publishedAt") or raw.get("updatedAt")
        posted_dt = None
        if posted:
            try:
                posted_dt = datetime.fromisoformat(str(posted).replace("Z", "+00:00"))
            except ValueError:
                posted_dt = None
        remote = "remote" if raw.get("isRemote") else None
        return NormalizedJob(
            job_id=str(raw.get("id")),
            source=self.source,
            company=raw.get("_board", "unknown"),
            title=raw.get("title", ""),
            location=raw.get("location"),
            description=raw.get("descriptionPlain") or raw.get("description"),
            experience=None,
            apply_url=raw.get("applyUrl") or raw.get("jobUrl"),
            posted_date=posted_dt,
            employment_type=raw.get("employmentType"),
            remote_status=remote,
            raw={k: v for k, v in raw.items() if k not in ("description", "descriptionPlain")},
        )

    def health_check(self) -> HealthResult:
        boards = self._boards()
        if not boards:
            return HealthResult(False, "no boards configured")
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                r = client.get(f"{BASE}/{boards[0]}")
                r.raise_for_status()
            return HealthResult(True, "reachable")
        except Exception as e:  # noqa: BLE001
            return HealthResult(False, str(e))
