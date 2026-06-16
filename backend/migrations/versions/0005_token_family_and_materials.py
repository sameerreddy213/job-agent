"""token family tracking + materials table

Revision ID: 0005_token_family_and_materials
Revises: 0004_resume_intelligence
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_token_family_and_materials"
down_revision = "0004_resume_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    op.create_table(
        "materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resume_category", sa.String(), nullable=True),
        sa.Column("cover_letter_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("cover_letter_text", sa.Text(), nullable=True),
        sa.Column("resume_summary_text", sa.Text(), nullable=True),
        sa.Column("application_answers", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("txt_path", sa.String(), nullable=True),
        sa.Column("docx_path", sa.String(), nullable=True),
        sa.Column("pdf_path", sa.String(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", name="uq_materials_job_id"),
    )


def downgrade() -> None:
    op.drop_table("materials")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "family_id")
