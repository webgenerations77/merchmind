"""Add text_concept_scoring to designs

Revision ID: 012
Revises: 011
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("designs", sa.Column("text_concept_scoring", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("designs", "text_concept_scoring")
