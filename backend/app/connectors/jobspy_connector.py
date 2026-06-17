"""JobSpy-backed connectors (LinkedIn, Naukri, Indeed) — free, no API token.

Replaces the paid Apify actors. JobSpy (`python-jobspy`) scrapes the portals
directly and returns a pandas DataFrame with a normalized schema across sites,
including the direct apply URL and any e-mail parsed from the description.

We run one site per connector so each Source keeps its own run_health, config,
and schedule. Tune volume via Source.config to stay under single-IP rate limits:

  { "search_term": "software engineer", "location": "India",
    "results_wanted": 30, "hours_old": 720 }

Anti-bot note: from one server IP LinkedIn may occasionally throttle. Keep
results_wanted modest and SCAN_INTERVAL_MINUTES spaced; add proxies only if you
later need heavy volume.
"""
from datetime import datetime, time

from .base import BaseConnector, HealthResult, NormalizedJob


def _clean(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in {"nan", "none", "null"}:
        return None
    return s


def _first_email(v) -> str | None:
    """JobSpy `emails` may be a list, a comma string, or NaN."""
    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        for e in v:
            e = _clean(e)
            if e:
                return e
        return None
    s = _clean(v)
    if not s:
        return None
    return s.split(",")[0].strip() or None


class _JobSpyConnector(BaseConnector):
    """Generic JobSpy site runner. Subclasses set `source` + `site`."""

    source = "jobspy"
    site: str = ""  # JobSpy site_name (linkedin|naukri|indeed)

    default_search_term = "software engineer"
    default_location = "India"
    default_results_wanted = 30
    default_hours_old = 720  # last 30 days

    def _cfg(self, key: str, default):
        val = self.config.get(key)
        return val if val not in (None, "") else default

    def discover_jobs(self) -> list[dict]:
        # Imported lazily so a missing optional dep can't break app import.
        from jobspy import scrape_jobs

        kwargs = dict(
            site_name=[self.site],
            search_term=self._cfg("search_term", self.default_search_term),
            location=self._cfg("location", self.default_location),
            results_wanted=int(self._cfg("results_wanted", self.default_results_wanted)),
            hours_old=int(self._cfg("hours_old", self.default_hours_old)),
            country_indeed="India",
            linkedin_fetch_description=self.site == "linkedin",
            verbose=0,
        )
        if self.config.get("is_remote") is not None:
            kwargs["is_remote"] = bool(self.config["is_remote"])

        df = scrape_jobs(**kwargs)
        if df is None or len(df) == 0:
            return []
        return df.to_dict(orient="records")

    def normalize_job(self, raw: dict) -> NormalizedJob:
        company = _clean(raw.get("company")) or "unknown"
        title = _clean(raw.get("title")) or ""
        # Prefer the employer-direct URL when JobSpy resolved one.
        apply_url = _clean(raw.get("job_url_direct")) or _clean(raw.get("job_url"))

        posted_dt = None
        dp = raw.get("date_posted")
        if dp is not None and _clean(dp):
            try:
                # JobSpy gives a date; store as midnight UTC-naive datetime.
                posted_dt = datetime.combine(
                    datetime.fromisoformat(str(dp)[:10]).date(), time.min
                )
            except (ValueError, TypeError):
                posted_dt = None

        nj = NormalizedJob(
            job_id=_clean(raw.get("id")) or apply_url or f"{company}-{title}",
            source=self.source,
            company=company,
            title=title,
            location=_clean(raw.get("location")),
            description=_clean(raw.get("description")),
            apply_url=apply_url,
            employment_type=_clean(raw.get("job_type")),
            remote_status="remote" if raw.get("is_remote") else None,
            posted_date=posted_dt,
            raw={"emails": raw.get("emails"), "site": raw.get("site")},
        )
        # Carry any parsed e-mail so the pipeline can surface it for outreach.
        nj.raw["contact_email"] = _first_email(raw.get("emails"))
        return nj

    def health_check(self) -> HealthResult:
        try:
            import jobspy  # noqa: F401
        except Exception as e:  # noqa: BLE001
            return HealthResult(False, f"jobspy not installed: {e}")
        return HealthResult(True, f"jobspy site={self.site}")


class JobSpyLinkedInConnector(_JobSpyConnector):
    source = "linkedin"
    site = "linkedin"


class JobSpyNaukriConnector(_JobSpyConnector):
    source = "naukri"
    site = "naukri"


class JobSpyIndeedConnector(_JobSpyConnector):
    source = "indeed"
    site = "indeed"
