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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
