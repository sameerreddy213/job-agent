"""profile extension: extended identity, contact, education, preferences

Revision ID: 0012_profile_extension
Revises: 0011_manual_apply
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_profile_extension"
down_revision = "0011_manual_apply"
branch_labels = None
depends_on = None

# All new profile columns are nullable free-text (forms vary widely).
_COLUMNS = [
    "first_name", "middle_name", "last_name", "college_email",
    "date_of_birth", "gender", "nationality",
    "address_line", "city", "state", "pincode", "preferred_locations",
    "qualification", "college_name", "degree", "branch",
    "joined_date", "graduation_date", "graduation_year", "cgpa",
    "class12_board", "class12_stream", "class12_school", "class12_percentage", "class12_year",
    "class10_board", "class10_school", "class10_percentage", "class10_year",
    "languages", "current_ctc", "shift_preference",
]


def upgrade() -> None:
    for col in _COLUMNS:
        op.add_column("profile", sa.Column(col, sa.String(), nullable=True))


def downgrade() -> None:
    for col in reversed(_COLUMNS):
        op.drop_column("profile", col)
