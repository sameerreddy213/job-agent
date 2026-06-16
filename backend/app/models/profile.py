from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Profile(Base):
    """Singleton row (id = 1) holding identity used for application form-fill."""

    __tablename__ = "profile"
    __table_args__ = (CheckConstraint("id = 1", name="profile_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(CITEXT(), nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    notice_period: Mapped[str | None] = mapped_column(String, nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String, nullable=True)
    work_auth: Mapped[str | None] = mapped_column(String, nullable=True)
    relocation: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    expected_ctc: Mapped[str | None] = mapped_column(String, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String, nullable=True)
    github_url: Mapped[str | None] = mapped_column(String, nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # ---- Extended identity / contact (Phase 8D profile extension) ----
    # All nullable & stored as free text so application forms stay flexible.
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    middle_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    college_email: Mapped[str | None] = mapped_column(String, nullable=True)
    date_of_birth: Mapped[str | None] = mapped_column(String, nullable=True)  # YYYY-MM-DD
    gender: Mapped[str | None] = mapped_column(String, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String, nullable=True)
    address_line: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str | None] = mapped_column(String, nullable=True)
    pincode: Mapped[str | None] = mapped_column(String, nullable=True)
    preferred_locations: Mapped[str | None] = mapped_column(String, nullable=True)

    # ---- Education ----
    qualification: Mapped[str | None] = mapped_column(String, nullable=True)
    college_name: Mapped[str | None] = mapped_column(String, nullable=True)
    degree: Mapped[str | None] = mapped_column(String, nullable=True)
    branch: Mapped[str | None] = mapped_column(String, nullable=True)
    joined_date: Mapped[str | None] = mapped_column(String, nullable=True)
    graduation_date: Mapped[str | None] = mapped_column(String, nullable=True)
    graduation_year: Mapped[str | None] = mapped_column(String, nullable=True)
    cgpa: Mapped[str | None] = mapped_column(String, nullable=True)
    class12_board: Mapped[str | None] = mapped_column(String, nullable=True)
    class12_stream: Mapped[str | None] = mapped_column(String, nullable=True)
    class12_school: Mapped[str | None] = mapped_column(String, nullable=True)
    class12_percentage: Mapped[str | None] = mapped_column(String, nullable=True)
    class12_year: Mapped[str | None] = mapped_column(String, nullable=True)
    class10_board: Mapped[str | None] = mapped_column(String, nullable=True)
    class10_school: Mapped[str | None] = mapped_column(String, nullable=True)
    class10_percentage: Mapped[str | None] = mapped_column(String, nullable=True)
    class10_year: Mapped[str | None] = mapped_column(String, nullable=True)

    # ---- Work / preferences ----
    languages: Mapped[str | None] = mapped_column(String, nullable=True)
    current_ctc: Mapped[str | None] = mapped_column(String, nullable=True)
    shift_preference: Mapped[str | None] = mapped_column(String, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
