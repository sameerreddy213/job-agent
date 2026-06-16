"""Greenhouse public job-board API connector.

Endpoint: https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true
Config:   {"boards": ["stripe", "airbnb", ...]}  (company board tokens)
"""
import re
from datetime import datetime

import httpx

from ..config import settings
from .base import BaseConnector, HealthResult, NormalizedJob

BASE = "https://boards-api.greenhouse.io/v1/boards"
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str | None) -> str | None:
    if not text:
        return None
    return _TAG_RE.sub(" ", text).replace("&nbsp;", " ").strip()


class GreenhouseConnector(BaseConnector):
    source = "greenhouse"

    def _boards(self) -> list[str]:
        return self.config.get("boards", [])

    def discover_jobs(self) -> list[dict]:
        jobs: list[dict] = []
        with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
            for board in self._boards():
                try:
                    resp = client.get(f"{BASE}/{board}/jobs", params={"content": "true"})
                    resp.raise_for_status()
                except Exception:
                    continue  # bad/unknown board token — skip, don't abort the run
                for j in resp.json().get("jobs", []):
                    j["_board"] = board
                    jobs.append(j)
        return jobs

    def normalize_job(self, raw: dict) -> NormalizedJob:
        posted = raw.get("updated_at") or raw.get("first_published")
        posted_dt = None
        if posted:
            try:
                posted_dt = datetime.fromisoformat(posted.replace("Z", "+00:00"))
            except ValueError:
                posted_dt = None
        return NormalizedJob(
            job_id=str(raw.get("id")),
            source=self.source,
            company=raw.get("_board", "unknown"),
            title=raw.get("title", ""),
            location=(raw.get("location") or {}).get("name"),
            description=_strip_html(raw.get("content")),
            experience=None,
            apply_url=raw.get("absolute_url"),
            posted_date=posted_dt,
            employment_type=None,
            remote_status=None,
            raw={k: v for k, v in raw.items() if k != "content"},
        )

    def health_check(self) -> HealthResult:
        boards = self._boards()
        if not boards:
            return HealthResult(False, "no boards configured")
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                r = client.get(f"{BASE}/{boards[0]}/jobs")
                r.raise_for_status()
            return HealthResult(True, "reachable")
        except Exception as e:  # noqa: BLE001
            return HealthResult(False, str(e))
