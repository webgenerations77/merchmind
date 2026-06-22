"""Add featured_at timestamp to designs

Revision ID: 016
Revises: 015
"""
from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("designs", sa.Column("featured_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("designs", "featured_at")
