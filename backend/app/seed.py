"""Seed the admin user and default sources from env. Idempotent."""
from .config import settings
from .database import SessionLocal
from .models.source import Source
from .models.user import User
from .security import hash_password

# Default sources (manual-apply policy; this app never auto-submits).
DEFAULT_SOURCES = [
    {"name": "greenhouse", "kind": "ats", "apply_policy": "manual"},
    {"name": "lever", "kind": "ats", "apply_policy": "manual"},
    {"name": "ashby", "kind": "ats", "apply_policy": "manual"},
    {"name": "linkedin", "kind": "ats", "apply_policy": "manual"},
]

# Best-effort India starter set. Some board tokens may be invalid — connectors
# skip unknown boards instead of failing. Refine the exact tokens on the Sources
# page (each source's company/board list is editable there).
STARTER_CONFIG: dict[str, dict] = {
    "greenhouse": {"boards": [
        "razorpay", "postman", "freshworks", "innovaccer", "groww",
        "zeta", "mindtickle", "hasura",
    ]},
    "lever": {"companies": [
        "leadsquared", "darwinbox", "browserstack", "chargebee",
    ]},
    "ashby": {"boards": ["razorpay", "zepto"]},
    "linkedin": {"input": {
        "title": "software engineer fresher",
        "location": "India",
        "rows": 50,
    }},
}


def seed_admin() -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        if existing:
            print(f"[seed] admin '{settings.ADMIN_USERNAME}' already exists.")
            return
        db.add(
            User(
                username=settings.ADMIN_USERNAME,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
            )
        )
        db.commit()
        print(f"[seed] created admin '{settings.ADMIN_USERNAME}'.")
    finally:
        db.close()


def seed_sources() -> None:
    db = SessionLocal()
    try:
        for spec in DEFAULT_SOURCES:
            existing = db.query(Source).filter(Source.name == spec["name"]).first()
            if existing is None:
                db.add(Source(config=STARTER_CONFIG.get(spec["name"], {}), **spec))
            elif not existing.config:
                # Backfill the starter config for a source created before this set
                # existed (never overwrites a config you've already customised).
                existing.config = STARTER_CONFIG.get(spec["name"], {})
        db.commit()
        print("[seed] default sources ensured (starter config applied where empty).")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
    seed_sources()
