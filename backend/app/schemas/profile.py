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

    # Extended identity / contact (profile extension)
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    college_email: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None
    nationality: str | None = None
    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    preferred_locations: str | None = None

    # Education
    qualification: str | None = None
    college_name: str | None = None
    degree: str | None = None
    branch: str | None = None
    joined_date: str | None = None
    graduation_date: str | None = None
    graduation_year: str | None = None
    cgpa: str | None = None
    class12_board: str | None = None
    class12_stream: str | None = None
    class12_school: str | None = None
    class12_percentage: str | None = None
    class12_year: str | None = None
    class10_board: str | None = None
    class10_school: str | None = None
    class10_percentage: str | None = None
    class10_year: str | None = None

    # Work / preferences
    languages: str | None = None
    current_ctc: str | None = None
    shift_preference: str | None = None


class ProfileUpdate(ProfileBase):
    """All fields required except the optionals above (upsert of the singleton)."""


class ProfileOut(ProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    updated_at: datetime
