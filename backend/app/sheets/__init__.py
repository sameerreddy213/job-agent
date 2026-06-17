"""Google Sheets one-way mirror (Phase 6B).

Database is the source of truth; this package pushes a read-only mirror into a
Google Sheet (tabs: Jobs, Applications, Sources, Runs, Resume Stats) for
reporting/review. Auth via env-based service-account credentials.
"""
from .client import is_configured
from .pull import pull_changes
from .sync import sync_all

__all__ = ["sync_all", "pull_changes", "is_configured"]
