"""Sample connector for TEST_MODE.

Generates a deterministic synthetic dataset (default 50 jobs) so the pipeline —
filtering, scoring, deduplication, and the API — can be exercised without
hitting Greenhouse/Lever/Ashby. Includes intentional variety:
  - fresher / entry-level roles (should pass + score high)
  - senior / "2+ years" roles (should be filtered out)
  - target cities, remote/hybrid, and off-target cities
  - deliberate duplicates (same company+title+location) to trigger dedupe
"""
from datetime import datetime, timedelta, timezone

from ..config import settings
from .base import BaseConnector, HealthResult, NormalizedJob

_SOURCES = ["greenhouse", "lever", "ashby"]
_COMPANIES = ["Acme", "Globex", "Initech", "Umbrella", "Hooli", "Stark", "Wayne"]
_TARGET = ["Hyderabad", "Bangalore", "Pune", "Chennai", "Noida", "Gurugram"]
_OFFTARGET = ["London", "Berlin", "Singapore", "New York"]

# (title, description-snippet) — mix of accept/reject signals
_ROLES = [
    ("Software Engineer", "Hiring freshers. 0-1 year experience. React, Node, MongoDB."),
    ("SDE-1", "Entry level graduate role. Java, Spring, SQL. Freshers welcome."),
    ("Frontend Developer", "Graduate role. React, TypeScript, CSS, Redux."),
    ("Backend Developer", "Fresher backend role. Node.js, Express, PostgreSQL."),
    ("MERN Stack Developer", "Entry-level MERN. MongoDB, Express, React, Node."),
    ("Associate Software Engineer", "Trainee program for fresh graduates. Python, SQL."),
    ("Java Developer", "0-1 year Java developer. Spring Boot, REST, Git."),
    ("React Developer", "Junior React developer. Next.js, TypeScript, Redux."),
    ("Senior Software Engineer", "5+ years experience required. Leadership skills."),
    ("Engineering Manager", "Manage a team. 8+ years experience."),
    ("Backend Developer", "Requires 2+ years experience in Node.js and AWS."),
    ("Principal Architect", "10+ years. Architecture ownership."),
]


class SampleConnector(BaseConnector):
    source = "sample"

    def discover_jobs(self) -> list[dict]:
        count = settings.SAMPLE_JOB_COUNT
        now = datetime.now(timezone.utc)
        rows: list[dict] = []
        for i in range(count):
            role_title, role_desc = _ROLES[i % len(_ROLES)]
            company = _COMPANIES[i % len(_COMPANIES)]
            # Every 7th job uses an off-target city; rest cycle target cities.
            if i % 11 == 0:
                location = "Remote, India"
            elif i % 7 == 0:
                location = _OFFTARGET[i % len(_OFFTARGET)]
            else:
                location = _TARGET[i % len(_TARGET)]
            source = _SOURCES[i % len(_SOURCES)]
            rows.append(
                {
                    "id": f"sample-{i}",
                    "source": source,
                    "company": company,
                    "title": role_title,
                    "location": location,
                    "description": role_desc,
                    "apply_url": f"https://example.test/{source}/{company}/{i}",
                    "posted_date": (now - timedelta(days=i % 14)).isoformat(),
                    "employment_type": "Full-time",
                    "remote_status": "remote" if "Remote" in location else None,
                }
            )
        # Inject 3 exact duplicates (same company+title+location) to test dedupe.
        for j in range(3):
            dup = dict(rows[j])
            dup["id"] = f"sample-dup-{j}"
            rows.append(dup)
        return rows

    def normalize_job(self, raw: dict) -> NormalizedJob:
        posted = raw.get("posted_date")
        posted_dt = None
        if posted:
            try:
                posted_dt = datetime.fromisoformat(posted)
            except ValueError:
                posted_dt = None
        return NormalizedJob(
            job_id=str(raw["id"]),
            source=raw.get("source", self.source),
            company=raw["company"],
            title=raw["title"],
            location=raw.get("location"),
            description=raw.get("description"),
            experience=None,
            apply_url=raw.get("apply_url"),
            posted_date=posted_dt,
            employment_type=raw.get("employment_type"),
            remote_status=raw.get("remote_status"),
            raw=raw,
        )

    def health_check(self) -> HealthResult:
        return HealthResult(True, "sample connector always healthy")
