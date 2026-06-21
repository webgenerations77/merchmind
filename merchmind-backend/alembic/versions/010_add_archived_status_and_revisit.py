"""Add archived status to design_status enum, revisit_count and archived_at columns

Revision ID: 009
Revises: 008
"""
from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE design_status ADD VALUE IF NOT EXISTS 'archived'")
    op.add_column("designs", sa.Column("revisit_count", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("designs", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("designs", "archived_at")
    op.drop_column("designs", "revisit_count")
