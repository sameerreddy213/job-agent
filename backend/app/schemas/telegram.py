from pydantic import BaseModel, ConfigDict


class TelegramSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enabled: bool
    chat_id: str | None = None
    pref_high_match: bool
    pref_daily: bool
    pref_evening: bool
    pref_pipeline_failure: bool
    pref_sheets_failure: bool
    pref_security: bool
    # Whether a bot token is present in the environment (token is never returned).
    configured: bool = False


class TelegramSettingsUpdate(BaseModel):
    enabled: bool | None = None
    chat_id: str | None = None
    pref_high_match: bool | None = None
    pref_daily: bool | None = None
    pref_evening: bool | None = None
    pref_pipeline_failure: bool | None = None
    pref_sheets_failure: bool | None = None
    pref_security: bool | None = None
