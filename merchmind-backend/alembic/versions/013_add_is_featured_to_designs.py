"""Add is_featured to designs

Revision ID: 013
Revises: 012
"""
from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("designs", sa.Column("is_featured", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("designs", "is_featured")
