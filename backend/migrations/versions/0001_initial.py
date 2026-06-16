"""initial schema: users, profile, resumes, resume_versions

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "citext"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("username", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="admin"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )

    op.create_table(
        "profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("notice_period", sa.String(), nullable=True),
        sa.Column("experience_level", sa.String(), nullable=True),
        sa.Column("work_auth", sa.String(), nullable=True),
        sa.Column("relocation", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("expected_ctc", sa.String(), nullable=True),
        sa.Column("linkedin_url", sa.String(), nullable=True),
        sa.Column("github_url", sa.String(), nullable=True),
        sa.Column("portfolio_url", sa.String(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("id = 1", name="profile_singleton"),
    )

    op.create_table(
        "resumes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("category", name="uq_resumes_category"),
    )

    op.create_table(
        "resume_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column(
            "skills_detected",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("role_category", sa.String(), nullable=False),
        sa.Column(
            "upload_date",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(
            ["resume_id"], ["resumes.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("resume_id", "version_number", name="uq_resume_version"),
    )
    op.create_index(
        "ix_resume_versions_resume_id", "resume_versions", ["resume_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_resume_versions_resume_id", table_name="resume_versions")
    op.drop_table("resume_versions")
    op.drop_table("resumes")
    op.drop_table("profile")
    op.drop_table("users")
