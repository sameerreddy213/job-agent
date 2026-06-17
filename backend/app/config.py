"""Application settings loaded from environment (.env)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+psycopg://jobagent:jobagent@postgres:5432/jobagent"

    # Auth / JWT
    JWT_SECRET: str = "change_me"
    JWT_ACCESS_TTL_MIN: int = 30
    JWT_REFRESH_TTL_DAYS: int = 7

    # Login rate limiting (per username, in-process sliding window)
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_SECONDS: int = 300

    # Admin seed
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change_me_strong_password"

    # Scoring thresholds (used in later phases)
    SCORE_AUTO_APPROVE: int = 90
    SCORE_REVIEW: int = 70

    # Retention (later phases)
    DATA_RETENTION_DAYS: int = 365

    # Storage
    RESUME_DIR: str = "/data/resumes"
    GENERATED_DIR: str = "/data/generated"

    # Telegram (Phase 6C) — token is always env-only (secret); chat_id/prefs in DB
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_POLL_INTERVAL_SECONDS: int = 15

    # Google Sheets mirror (Phase 6B)
    GOOGLE_SHEET_ID: str = ""
    GOOGLE_SERVICE_ACCOUNT_FILE: str = ""
    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""  # inline JSON (preferred over file)
    SHEETS_SYNC_ENABLED: bool = False
    SHEETS_SYNC_INTERVAL_MINUTES: int = 30

    # Pipeline / scheduler
    SCAN_INTERVAL_MINUTES: int = 60
    TEST_MODE: bool = False
    SAMPLE_JOB_COUNT: int = 50
    HTTP_TIMEOUT_SECONDS: int = 20
    # run_health WARNING if a source returns fewer than this many jobs
    HEALTH_MIN_JOBS_WARNING: int = 1

    # Hard filters (pipeline). India-only rejects jobs whose location is clearly
    # outside India; unknown/empty locations are kept for review.
    INDIA_ONLY: bool = True

    # Apify (LinkedIn scraping). Token is env-only (secret); the actor + search
    # input live in the "linkedin" Source.config.
    APIFY_TOKEN: str = ""
    APIFY_DEFAULT_ACTOR: str = "curious_coder~linkedin-jobs-scraper"

    # AI provider (Phase 8D / WI-3) — optional. When AI_PROVIDER=openrouter and
    # AI_API_KEY is set, materials are LLM-polished; otherwise deterministic
    # templates are used unchanged. OpenRouter is OpenAI-compatible.
    AI_PROVIDER: str = ""           # "" (off) | "openrouter"
    AI_API_KEY: str = ""
    # Free-only model pool. The client rotates through these and switches to the
    # next when one is rate-limited/unavailable. Only ":free" slugs are used.
    AI_MODELS: str = (
        "meta-llama/llama-3.3-70b-instruct:free,"
        "google/gemini-2.0-flash-exp:free,"
        "deepseek/deepseek-chat-v3-0324:free,"
        "qwen/qwen-2.5-72b-instruct:free,"
        "mistralai/mistral-small-3.1-24b-instruct:free"
    )
    AI_MODEL: str = ""              # optional single override; must be a ":free" slug
    AI_BASE_URL: str = "https://openrouter.ai/api/v1"
    AI_MAX_TOKENS: int = 900
    AI_TIMEOUT_SECONDS: int = 30


settings = Settings()
