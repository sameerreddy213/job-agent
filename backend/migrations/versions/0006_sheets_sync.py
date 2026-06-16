"""sheets sync state/log + run_health filtered/scored counters

Revision ID: 0006_sheets_sync
Revises: 0005_token_family_and_materials
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_sheets_sync"
down_revision = "0005_token_family_and_materials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("run_health", sa.Column("filtered", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("run_health", sa.Column("scored", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "sync_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("jobs_cursor", sa.DateTime(timezone=True), nullable=True),
        sa.Column("runs_cursor", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("id = 1", name="sync_state_singleton"),
    )

    op.create_table(
        "sheet_sync_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("run_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("rows_written", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("tabs", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_sheet_sync_runs_run_at", "sheet_sync_runs", ["run_at"])


def downgrade() -> None:
    op.drop_index("ix_sheet_sync_runs_run_at", table_name="sheet_sync_runs")
    op.drop_table("sheet_sync_runs")
    op.drop_table("sync_state")
    op.drop_column("run_health", "scored")
    op.drop_column("run_health", "filtered")
