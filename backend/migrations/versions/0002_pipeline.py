"""phase 2: sources, jobs, job_scores, run_health

Revision ID: 0002_pipeline
Revises: 0001_initial
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_pipeline"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("apply_policy", sa.String(), nullable=False, server_default="auto"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_run", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("name", name="uq_sources_name"),
    )

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("company", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("experience", sa.String(), nullable=True),
        sa.Column("apply_url", sa.String(), nullable=True),
        sa.Column("posted_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("employment_type", sa.String(), nullable=True),
        sa.Column("remote_status", sa.String(), nullable=True),
        sa.Column("raw", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(), nullable=False, server_default="DISCOVERED"),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("fingerprint", name="uq_jobs_fingerprint"),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_source", "jobs", ["source"])
    op.create_index("ix_jobs_discovered_at", "jobs", ["discovered_at"])

    op.create_table(
        "job_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("freshers_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skills_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("location_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("role_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("classification", sa.String(), nullable=False),
        sa.Column("matched_resume_category", sa.String(), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("passed_filters", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("scored_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", name="uq_job_scores_job_id"),
    )
    op.create_index("ix_job_scores_total", "job_scores", ["total_score"])

    op.create_table(
        "run_health",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("jobs_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("response_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
    )
    op.create_index("ix_run_health_run_at", "run_health", ["run_at"])


def downgrade() -> None:
    op.drop_index("ix_run_health_run_at", table_name="run_health")
    op.drop_table("run_health")
    op.drop_index("ix_job_scores_total", table_name="job_scores")
    op.drop_table("job_scores")
    op.drop_index("ix_jobs_discovered_at", table_name="jobs")
    op.drop_index("ix_jobs_source", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("sources")
