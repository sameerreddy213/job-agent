"""ATS integration layer: ats fields on applications (Phase 8B)

Revision ID: 0010_ats_layer
Revises: 0009_applications
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_ats_layer"
down_revision = "0009_applications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("ats_type", sa.String(), server_default="UNKNOWN", nullable=False))
    op.add_column("applications", sa.Column("ats_version", sa.String(), nullable=True))
    op.add_column("applications", sa.Column("application_url", sa.String(), nullable=True))
    op.add_column("applications", sa.Column("supports_easy_apply", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("applications", sa.Column("requires_manual_fields", sa.Boolean(), server_default="true", nullable=False))
    op.create_index("ix_applications_ats_type", "applications", ["ats_type"])


def downgrade() -> None:
    op.drop_index("ix_applications_ats_type", table_name="applications")
    op.drop_column("applications", "requires_manual_fields")
    op.drop_column("applications", "supports_easy_apply")
    op.drop_column("applications", "application_url")
    op.drop_column("applications", "ats_version")
    op.drop_column("applications", "ats_type")
