from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class ProfileBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    location: str
    notice_period: str | None = None
    experience_level: str | None = None
    work_auth: str | None = None
    relocation: bool = True
    expected_ctc: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None


class ProfileUpdate(ProfileBase):
    """All fields required except the optionals above (upsert of the singleton)."""


class ProfileOut(ProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    updated_at: datetime
