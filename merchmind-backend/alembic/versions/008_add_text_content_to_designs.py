"""Add primary_text, secondary_text, tagline columns to designs

Revision ID: 008
Revises: 007
"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("designs", sa.Column("primary_text", sa.Text(), nullable=True))
    op.add_column("designs", sa.Column("secondary_text", sa.Text(), nullable=True))
    op.add_column("designs", sa.Column("tagline", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("designs", "tagline")
    op.drop_column("designs", "secondary_text")
    op.drop_column("designs", "primary_text")
