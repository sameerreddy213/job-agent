"""refresh tokens, blacklists, audit log, source metadata

Revision ID: 0003_auth_blacklist_audit
Revises: 0002_pipeline
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_auth_blacklist_audit"
down_revision = "0002_pipeline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- source configuration metadata ---
    op.add_column("sources", sa.Column("display_name", sa.String(), nullable=True))
    op.add_column("sources", sa.Column("website", sa.String(), nullable=True))
    op.add_column("sources", sa.Column("rate_limit_per_min", sa.Integer(), nullable=True))
    op.add_column(
        "sources",
        sa.Column("meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    # --- refresh tokens ---
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("jti", sa.String(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("jti", name="uq_refresh_tokens_jti"),
    )

    # --- company blacklist ---
    op.create_table(
        "company_blacklist",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("company", postgresql.CITEXT(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("company", name="uq_company_blacklist_company"),
    )

    # --- keyword blacklist ---
    op.create_table(
        "keyword_blacklist",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("keyword", postgresql.CITEXT(), nullable=False),
        sa.Column("applies_to", sa.String(), nullable=False, server_default="both"),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("keyword", name="uq_keyword_blacklist_keyword"),
    )

    # --- audit log ---
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity", sa.String(), nullable=True),
        sa.Column("entity_id", sa.String(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_action", table_name="audit_log")
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_table("keyword_blacklist")
    op.drop_table("company_blacklist")
    op.drop_table("refresh_tokens")
    op.drop_column("sources", "meta")
    op.drop_column("sources", "rate_limit_per_min")
    op.drop_column("sources", "website")
    op.drop_column("sources", "display_name")
