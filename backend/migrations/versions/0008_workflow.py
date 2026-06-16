"""workflow state machine: job_state_history, snoozed_until, status migration

Revision ID: 0008_workflow
Revises: 0007_telegram
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_workflow"
down_revision = "0007_telegram"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "job_state_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_state", sa.String(), nullable=True),
        sa.Column("new_state", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_job_state_history_job_id", "job_state_history", ["job_id"])
    op.create_index("ix_job_state_history_new_state", "job_state_history", ["new_state"])

    # Migrate legacy classification-based statuses to workflow states.
    op.execute("UPDATE jobs SET status = 'REVIEW_QUEUE' WHERE status = 'AUTO_APPROVE_ELIGIBLE'")
    op.execute("UPDATE jobs SET status = 'REJECTED' WHERE status = 'REJECT'")
    op.execute("UPDATE jobs SET status = 'FILTERED' WHERE status = 'REJECTED_FILTER'")


def downgrade() -> None:
    op.execute("UPDATE jobs SET status = 'REJECTED_FILTER' WHERE status = 'FILTERED'")
    op.drop_index("ix_job_state_history_new_state", table_name="job_state_history")
    op.drop_index("ix_job_state_history_job_id", table_name="job_state_history")
    op.drop_table("job_state_history")
    op.drop_column("jobs", "snoozed_until")
