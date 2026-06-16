"""telegram settings + events + job high_match_notified flag

Revision ID: 0007_telegram
Revises: 0006_sheets_sync
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_telegram"
down_revision = "0006_sheets_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("high_match_notified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "telegram_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("chat_id", sa.String(), nullable=True),
        sa.Column("pref_high_match", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("pref_daily", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("pref_evening", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("pref_pipeline_failure", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("pref_sheets_failure", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("pref_security", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_update_id", sa.BigInteger(), nullable=True),
        sa.CheckConstraint("id = 1", name="telegram_settings_singleton"),
    )

    op.create_table(
        "telegram_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_telegram_events_created_at", "telegram_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_telegram_events_created_at", table_name="telegram_events")
    op.drop_table("telegram_events")
    op.drop_table("telegram_settings")
    op.drop_column("jobs", "high_match_notified")
