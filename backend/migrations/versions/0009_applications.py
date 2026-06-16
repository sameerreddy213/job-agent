"""application engine: applications, documents, answers, events (Phase 8A)

Revision ID: 0009_applications
Revises: 0008_workflow
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_applications"
down_revision = "0008_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(), server_default="NOT_STARTED", nullable=False),
        sa.Column("resume_category", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("job_id", name="uq_applications_job_id"),
    )
    op.create_index("ix_applications_status", "applications", ["status"])

    op.create_table(
        "application_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("fmt", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_application_documents_application_id", "application_documents", ["application_id"])

    op.create_table(
        "application_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_application_answers_application_id", "application_answers", ["application_id"])

    op.create_table(
        "application_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_state", sa.String(), nullable=True),
        sa.Column("new_state", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_application_events_application_id", "application_events", ["application_id"])
    op.create_index("ix_application_events_new_state", "application_events", ["new_state"])


def downgrade() -> None:
    op.drop_index("ix_application_events_new_state", table_name="application_events")
    op.drop_index("ix_application_events_application_id", table_name="application_events")
    op.drop_table("application_events")
    op.drop_index("ix_application_answers_application_id", table_name="application_answers")
    op.drop_table("application_answers")
    op.drop_index("ix_application_documents_application_id", table_name="application_documents")
    op.drop_table("application_documents")
    op.drop_index("ix_applications_status", table_name="applications")
    op.drop_table("applications")
