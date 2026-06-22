"""Add primary_product_type_reasoning to designs

Revision ID: 015
Revises: 014
"""
import sqlalchemy as sa
from alembic import op

revision = "015"
down_revision = "014"


def upgrade() -> None:
    op.add_column("designs", sa.Column("primary_product_type_reasoning", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("designs", "primary_product_type_reasoning")
