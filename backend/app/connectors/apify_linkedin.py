"""LinkedIn jobs via an Apify actor.

We don't scrape LinkedIn directly (anti-bot + ToS); instead we run a hosted
Apify actor and ingest its dataset. The actor + search input are configurable in
the "linkedin" Source.config so this works with whichever LinkedIn-jobs actor you
pick; field mapping tolerates the common output shapes across popular actors.

Source.config:
  {
    "actor": "misceres~linkedin-jobs-scraper",   # optional; defaults to settings
    "input": { ... actor-specific input ... }      # optional; sensible default built
  }
APIFY_TOKEN is read from the environment (secret).
"""
import httpx

from ..config import settings
from .base import BaseConnector, HealthResult, NormalizedJob

_RUN_SYNC = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"

# Default search: fresher software roles in India. Override via config["input"].
_DEFAULT_INPUT = {
    "title": "software engineer fresher",
    "location": "India",
    "rows": 50,
    "publishedAt": "r2592000",  # last 30 days (actor-dependent; ignored if unknown)
}


def _first(raw: dict, *keys: str) -> str | None:
    for k in keys:
        v = raw.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


class ApifyLinkedInConnector(BaseConnector):
    source = "linkedin"

    def _actor(self) -> str:
        return self.config.get("actor") or settings.APIFY_DEFAULT_ACTOR

    def _input(self) -> dict:
        return self.config.get("input") or _DEFAULT_INPUT

    def discover_jobs(self) -> list[dict]:
        if not settings.APIFY_TOKEN:
            raise RuntimeError("APIFY_TOKEN is not set")
        url = _RUN_SYNC.format(actor=self._actor())
        with httpx.Client(timeout=max(120, settings.HTTP_TIMEOUT_SECONDS)) as client:
            resp = client.post(url, params={"token": settings.APIFY_TOKEN}, json=self._input())
            resp.raise_for_status()
            items = resp.json()
        return items if isinstance(items, list) else []

    def normalize_job(self, raw: dict) -> NormalizedJob:
        company = _first(raw, "companyName", "company", "company_name", "organization") or "unknown"
        title = _first(raw, "title", "jobTitle", "position", "name") or ""
        location = _first(raw, "location", "jobLocation", "formattedLocation", "place")
        description = _first(raw, "descriptionText", "description", "jobDescription", "descriptionHtml")
        apply_url = _first(raw, "applyUrl", "jobUrl", "url", "link", "jobPostingUrl")
        remote = _first(raw, "workplaceType", "workType", "remote")
        employment = _first(raw, "employmentType", "contractType", "jobType")
        return NormalizedJob(
            job_id=str(raw.get("id") or raw.get("jobId") or apply_url or f"{company}-{title}"),
            source=self.source,
            company=company,
            title=title,
            location=location,
            description=description,
            apply_url=apply_url,
            employment_type=employment,
            remote_status=remote,
            raw=raw,
        )

    def health_check(self) -> HealthResult:
        if not settings.APIFY_TOKEN:
            return HealthResult(ok=False, detail="APIFY_TOKEN not set")
        return HealthResult(ok=True, detail=f"actor {self._actor()}")
