"""Apify-backed connectors (LinkedIn, Naukri, Internshala).

We don't scrape these portals directly (anti-bot + ToS); instead we run hosted
Apify actors and ingest their datasets. Each source picks its actor + input via
Source.config (editable on the Sources page); field mapping tolerates the common
output shapes across actors. APIFY_TOKEN is read from the environment (secret).

Source.config:
  { "actor": "<username~actor>", "input": { ...actor-specific input... } }
"""
import httpx

from ..config import settings
from .base import BaseConnector, HealthResult, NormalizedJob

_RUN_SYNC = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"


def _first(raw: dict, *keys: str) -> str | None:
    for k in keys:
        v = raw.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


class _ApifyConnector(BaseConnector):
    """Generic Apify actor runner. Subclasses set `source` + sensible defaults."""

    source = "apify"
    default_actor: str = ""
    default_input: dict = {}

    def _actor(self) -> str:
        return self.config.get("actor") or self.default_actor or settings.APIFY_DEFAULT_ACTOR

    def _input(self) -> dict:
        return self.config.get("input") or self.default_input

    def discover_jobs(self) -> list[dict]:
        if not settings.APIFY_TOKEN:
            raise RuntimeError("APIFY_TOKEN is not set")
        url = _RUN_SYNC.format(actor=self._actor())
        with httpx.Client(timeout=max(300, settings.HTTP_TIMEOUT_SECONDS)) as client:
            resp = client.post(url, params={"token": settings.APIFY_TOKEN}, json=self._input())
            resp.raise_for_status()
            items = resp.json()
        return items if isinstance(items, list) else []

    def normalize_job(self, raw: dict) -> NormalizedJob:
        company = _first(raw, "companyName", "company", "company_name", "organization", "company_name_text") or "unknown"
        title = _first(raw, "title", "jobTitle", "position", "name", "profile", "job_title") or ""
        location = _first(raw, "location", "jobLocation", "formattedLocation", "place", "city")
        description = _first(raw, "descriptionText", "description", "jobDescription", "descriptionHtml", "jd", "job_description")
        apply_url = _first(raw, "applyUrl", "apply_url", "jobUrl", "job_url", "url", "link", "jobPostingUrl", "jdURL", "detailUrl")
        remote = _first(raw, "workplaceType", "workMode", "work_mode", "remote")
        employment = _first(raw, "employmentType", "contractType", "jobType", "job_type")
        return NormalizedJob(
            job_id=str(raw.get("id") or raw.get("jobId") or raw.get("jobid") or apply_url or f"{company}-{title}"),
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


class ApifyLinkedInConnector(_ApifyConnector):
    source = "linkedin"
    default_actor = "curious_coder~linkedin-jobs-scraper"
    default_input = {
        "urls": [
            "https://www.linkedin.com/jobs/search/"
            "?keywords=software%20engineer&location=India&f_E=1%2C2&f_TPR=r2592000"
        ],
        "count": 50,
        "scrapeCompany": False,
    }


class NaukriConnector(_ApifyConnector):
    source = "naukri"
    default_actor = "muhammetakkurtt~naukri-job-scraper"
    default_input = {
        "keyword": "software developer",
        "experience": "0",      # 0 years -> freshers
        "freshness": "30",      # last 30 days
        "maxJobs": 50,
        "fetchDetails": True,   # include JD text (-> email extraction)
    }

    def normalize_job(self, raw: dict) -> NormalizedJob:
        # Naukri's actor nests the real fields under "jobDetails".
        jd = raw.get("jobDetails") or {}
        if not jd:
            return super().normalize_job(raw)
        title = (jd.get("title") or "").strip()
        company = (jd.get("staticCompanyName") or (jd.get("companyDetail") or {}).get("name") or "unknown").strip()
        description = jd.get("description") or jd.get("shortDescription")
        apply_url = jd.get("staticUrl") or jd.get("companyApplyUrl") or jd.get("applyRedirectUrl")
        if apply_url and not str(apply_url).startswith("http"):
            apply_url = "https://www.naukri.com/" + str(apply_url).lstrip("/")
        # locations: list of {label/name/city} or strings.
        loc = None
        locs = jd.get("locations")
        if isinstance(locs, list) and locs:
            parts = []
            for item in locs:
                if isinstance(item, dict):
                    parts.append(item.get("label") or item.get("name") or item.get("city") or "")
                elif isinstance(item, str):
                    parts.append(item)
            loc = ", ".join(p for p in parts if p) or None
        return NormalizedJob(
            job_id=str(jd.get("jobId") or apply_url or f"{company}-{title}"),
            source=self.source,
            company=company,
            title=title,
            location=loc,
            description=description if isinstance(description, str) else None,
            apply_url=apply_url,
            employment_type=jd.get("employmentType"),
            remote_status=str(jd.get("wfhType")) if jd.get("wfhType") else None,
            raw=raw,
        )


class InternshalaConnector(_ApifyConnector):
    source = "internshala"
    default_actor = "bareezh_codes~internshala-scrapper"
    default_input = {
        "job_category": "Software Development",
        "max_results": 50,
        "pages_to_scrape": 5,
        "work_from_home": True,
    }
