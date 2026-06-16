"""manual apply assistant: packet + ready confirmation on applications (Phase 8C)

Revision ID: 0011_manual_apply
Revises: 0010_ats_layer
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_manual_apply"
down_revision = "0010_ats_layer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("ready_confirmed", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("applications", sa.Column("ready_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("applications", sa.Column("packet_generated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("applications", sa.Column("packet_txt_path", sa.String(), nullable=True))
    op.add_column("applications", sa.Column("packet_docx_path", sa.String(), nullable=True))
    op.add_column("applications", sa.Column("packet_pdf_path", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("applications", "packet_pdf_path")
    op.drop_column("applications", "packet_docx_path")
    op.drop_column("applications", "packet_txt_path")
    op.drop_column("applications", "packet_generated_at")
    op.drop_column("applications", "ready_confirmed_at")
    op.drop_column("applications", "ready_confirmed")
