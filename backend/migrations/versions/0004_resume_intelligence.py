"""phase 5A: resume intelligence fields on job_scores and resume_versions

Revision ID: 0004_resume_intelligence
Revises: 0003_auth_blacklist_audit
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_resume_intelligence"
down_revision = "0003_auth_blacklist_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_scores", sa.Column("resume_match_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("job_scores", sa.Column("resume_confidence", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("job_scores", sa.Column("matched_skills", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("job_scores", sa.Column("missing_skills", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("job_scores", sa.Column("resume_reasoning", sa.Text(), nullable=True))
    op.add_column("job_scores", sa.Column("resume_override", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    op.add_column("resume_versions", sa.Column("detected_category", sa.String(), nullable=True))
    op.add_column("resume_versions", sa.Column("categorization_confidence", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("resume_versions", "categorization_confidence")
    op.drop_column("resume_versions", "detected_category")
    op.drop_column("job_scores", "resume_override")
    op.drop_column("job_scores", "resume_reasoning")
    op.drop_column("job_scores", "missing_skills")
    op.drop_column("job_scores", "matched_skills")
    op.drop_column("job_scores", "resume_confidence")
    op.drop_column("job_scores", "resume_match_score")
