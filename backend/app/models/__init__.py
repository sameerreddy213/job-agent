"""Model registry — import all models so Alembic/metadata sees them."""
from .user import User
from .profile import Profile
from .resume import Resume, ResumeVersion
from .source import Source
from .job import Job, JobScore, RunHealth
from .auth_token import RefreshToken
from .blacklist import CompanyBlacklist, KeywordBlacklist
from .audit import AuditLog
from .material import Material
from .sync import SheetSyncRun, SyncState
from .telegram import TelegramEvent, TelegramSettings
from .workflow import JobStateHistory
from .application import (
    Application,
    ApplicationAnswer,
    ApplicationDocument,
    ApplicationEvent,
)

__all__ = [
    "User", "Profile", "Resume", "ResumeVersion",
    "Source", "Job", "JobScore", "RunHealth",
    "RefreshToken", "CompanyBlacklist", "KeywordBlacklist", "AuditLog",
    "Material", "SyncState", "SheetSyncRun",
    "TelegramSettings", "TelegramEvent", "JobStateHistory",
    "Application", "ApplicationDocument", "ApplicationAnswer", "ApplicationEvent",
]
