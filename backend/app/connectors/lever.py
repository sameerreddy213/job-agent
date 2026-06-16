"""Lever public postings API connector.

Endpoint: https://api.lever.co/v0/postings/{company}?mode=json
Config:   {"companies": ["netflix", "..." ]}
"""
from datetime import datetime, timezone

import httpx

from ..config import settings
from .base import BaseConnector, HealthResult, NormalizedJob

BASE = "https://api.lever.co/v0/postings"


class LeverConnector(BaseConnector):
    source = "lever"

    def _companies(self) -> list[str]:
        return self.config.get("companies", [])

    def discover_jobs(self) -> list[dict]:
        jobs: list[dict] = []
        with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
            for company in self._companies():
                resp = client.get(f"{BASE}/{company}", params={"mode": "json"})
                resp.raise_for_status()
                for j in resp.json():
                    j["_company"] = company
                    jobs.append(j)
        return jobs

    def normalize_job(self, raw: dict) -> NormalizedJob:
        categories = raw.get("categories") or {}
        created = raw.get("createdAt")
        posted_dt = None
        if isinstance(created, (int, float)):
            posted_dt = datetime.fromtimestamp(created / 1000, tz=timezone.utc)
        return NormalizedJob(
            job_id=str(raw.get("id")),
            source=self.source,
            company=raw.get("_company", "unknown"),
            title=raw.get("text", ""),
            location=categories.get("location"),
            description=raw.get("descriptionPlain") or raw.get("description"),
            experience=None,
            apply_url=raw.get("hostedUrl") or raw.get("applyUrl"),
            posted_date=posted_dt,
            employment_type=categories.get("commitment"),
            remote_status=raw.get("workplaceType"),
            raw={k: v for k, v in raw.items() if k not in ("description", "descriptionPlain")},
        )

    def health_check(self) -> HealthResult:
        companies = self._companies()
        if not companies:
            return HealthResult(False, "no companies configured")
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                r = client.get(f"{BASE}/{companies[0]}", params={"mode": "json"})
                r.raise_for_status()
            return HealthResult(True, "reachable")
        except Exception as e:  # noqa: BLE001
            return HealthResult(False, str(e))
