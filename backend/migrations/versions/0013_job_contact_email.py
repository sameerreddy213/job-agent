"""jobs.contact_email — recruiter/contact email parsed from the JD

Revision ID: 0013_job_contact_email
Revises: 0012_profile_extension
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_job_contact_email"
down_revision = "0012_profile_extension"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("contact_email", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "contact_email")
