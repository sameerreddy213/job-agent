"""Seed DEMO data so the dashboard APIs have something to show before the UI exists.

Run inside the api container:
    docker compose exec api python -m app.seed_demo

Seeds:
  - admin user + default sources (via app.seed)
  - the owner profile
  - demo resume categories with a current version (placeholder file paths)
  - a couple of blacklist entries
  - then runs the discovery pipeline (TEST_MODE=true => 50 sample jobs)

Idempotent: safe to run repeatedly.
"""
from .config import settings
from .database import SessionLocal
from .models.blacklist import CompanyBlacklist, KeywordBlacklist
from .models.profile import Profile
from .models.resume import Resume, ResumeVersion
from .pipeline.runner import run_pipeline
from .seed import seed_admin, seed_sources

DEMO_PROFILE = dict(
    full_name="Tamalampudi Sameer Reddy",
    email="sameerreddy213@gmail.com",
    phone="+91 9652877199",
    location="Andhra Pradesh, India",
    notice_period="Immediate",
    experience_level="Fresher",
    work_auth="India",
    relocation=True,
    expected_ctc="8 LPA",
    linkedin_url="https://linkedin.com/in/sameerreddy213",
    github_url="https://github.com/sameerreddy213",
    portfolio_url=None,
)

DEMO_RESUMES = {
    "MERN_Stack": ["javascript", "react", "node", "express", "mongodb"],
    "Java_Developer": ["java", "spring", "sql", "rest"],
    "Frontend": ["react", "typescript", "css", "redux"],
}

DEMO_COMPANY_BLACKLIST = [("Initech", "demo: not interested")]
DEMO_KEYWORD_BLACKLIST = [("clearance", "both", "demo: requires clearance")]


def seed_profile() -> None:
    db = SessionLocal()
    try:
        if db.get(Profile, 1) is None:
            db.add(Profile(id=1, **DEMO_PROFILE))
            db.commit()
            print("[demo] profile seeded.")
        else:
            print("[demo] profile already present.")
    finally:
        db.close()


def seed_demo_resumes() -> None:
    db = SessionLocal()
    try:
        for category, skills in DEMO_RESUMES.items():
            if db.query(Resume).filter(Resume.category == category).first():
                continue
            resume = Resume(category=category)
            db.add(resume)
            db.flush()
            db.add(
                ResumeVersion(
                    resume_id=resume.id,
                    version_number=1,
                    file_path=f"{settings.RESUME_DIR}/{category}/v1_demo.pdf",
                    skills_detected=skills,
                    role_category=category,
                    is_current=True,
                )
            )
        db.commit()
        print("[demo] resume categories seeded.")
    finally:
        db.close()


def seed_demo_blacklists() -> None:
    db = SessionLocal()
    try:
        for company, reason in DEMO_COMPANY_BLACKLIST:
            if not db.query(CompanyBlacklist).filter(CompanyBlacklist.company == company).first():
                db.add(CompanyBlacklist(company=company, reason=reason))
        for kw, applies, reason in DEMO_KEYWORD_BLACKLIST:
            if not db.query(KeywordBlacklist).filter(KeywordBlacklist.keyword == kw).first():
                db.add(KeywordBlacklist(keyword=kw, applies_to=applies, reason=reason))
        db.commit()
        print("[demo] blacklists seeded.")
    finally:
        db.close()


def run_demo_pipeline() -> None:
    if not settings.TEST_MODE:
        print(
            "[demo] WARNING: TEST_MODE is false; pipeline will hit real sources "
            "(likely 0 jobs unless source configs are set). Set TEST_MODE=true for demo data."
        )
    db = SessionLocal()
    try:
        summary = run_pipeline(db)
        print(f"[demo] pipeline run (TEST_MODE={settings.TEST_MODE}): {summary}")
    finally:
        db.close()


def main() -> None:
    seed_admin()
    seed_sources()
    seed_profile()
    seed_demo_resumes()
    seed_demo_blacklists()
    run_demo_pipeline()
    print("[demo] done.")


if __name__ == "__main__":
    main()
