"""Seed the admin user and default sources from env. Idempotent."""
from .config import settings
from .database import SessionLocal
from .models.source import Source
from .models.user import User
from .security import hash_password

# Phase 2 default sources (ATS public boards; auto-apply policy).
DEFAULT_SOURCES = [
    {"name": "greenhouse", "kind": "ats", "apply_policy": "auto"},
    {"name": "lever", "kind": "ats", "apply_policy": "auto"},
    {"name": "ashby", "kind": "ats", "apply_policy": "auto"},
]


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
            if db.query(Source).filter(Source.name == spec["name"]).first():
                continue
            db.add(Source(config={}, **spec))
        db.commit()
        print("[seed] default sources ensured.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
    seed_sources()
