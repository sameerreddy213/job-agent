"""Internshala connector — direct, free (JobSpy doesn't cover Internshala).

Internshala has light anti-bot, so we fetch the public jobs listing pages and
parse the job cards. Config:

  { "category": "software-development", "work_from_home": true, "pages": 3 }

We read titles/company/location/apply-url from the listing cards (no per-job
detail fetch, to stay polite and fast).
"""
import httpx
from bs4 import BeautifulSoup

from ..config import settings
from .base import BaseConnector, HealthResult, NormalizedJob

BASE = "https://internshala.com"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}


def _txt(node) -> str | None:
    if node is None:
        return None
    s = node.get_text(" ", strip=True)
    return s or None


class InternshalaConnector(BaseConnector):
    source = "internshala"

    def _category(self) -> str:
        return self.config.get("category", "software-development")

    def _pages(self) -> int:
        return int(self.config.get("pages", 3))

    def _list_url(self, page: int) -> str:
        wfh = "work-from-home-" if self.config.get("work_from_home") else ""
        seg = f"{wfh}{self._category()}-jobs"
        suffix = f"/page-{page}" if page > 1 else ""
        return f"{BASE}/jobs/{seg}{suffix}/"

    def discover_jobs(self) -> list[dict]:
        out: list[dict] = []
        with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS, headers=_HEADERS,
                          follow_redirects=True) as client:
            for page in range(1, self._pages() + 1):
                try:
                    resp = client.get(self._list_url(page))
                    resp.raise_for_status()
                except Exception:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select("div.individual_internship")
                if not cards:
                    break  # no more results
                for card in cards:
                    out.append(self._parse_card(card))
        return [c for c in out if c]

    @staticmethod
    def _parse_card(card) -> dict | None:
        title_a = card.select_one("a.job-title-href") or card.select_one("h3 a")
        title = _txt(title_a)
        if not title:
            return None
        href = (title_a.get("href") if title_a else None) or card.get("data-href")
        apply_url = (BASE + href) if href and href.startswith("/") else href
        company = _txt(card.select_one("p.company-name")) or _txt(
            card.select_one(".company_name")
        )
        location = _txt(card.select_one(".locations")) or _txt(
            card.select_one(".location_link")
        )
        # Short detail bits (stipend/duration) give us a description stub.
        detail = _txt(card.select_one(".internship_other_details_container")) or _txt(
            card.select_one(".status-container")
        )
        return {
            "id": card.get("internshipid") or card.get("data-id") or apply_url,
            "title": title,
            "company": company,
            "location": location,
            "apply_url": apply_url,
            "description": detail,
        }

    def normalize_job(self, raw: dict) -> NormalizedJob:
        return NormalizedJob(
            job_id=str(raw.get("id") or raw.get("apply_url") or raw.get("title")),
            source=self.source,
            company=(raw.get("company") or "unknown").strip(),
            title=(raw.get("title") or "").strip(),
            location=raw.get("location"),
            description=raw.get("description"),
            apply_url=raw.get("apply_url"),
            raw=raw,
        )

    def health_check(self) -> HealthResult:
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS, headers=_HEADERS,
                              follow_redirects=True) as client:
                r = client.get(self._list_url(1))
                r.raise_for_status()
            return HealthResult(True, "reachable")
        except Exception as e:  # noqa: BLE001
            return HealthResult(False, str(e))
