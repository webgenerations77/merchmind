"""Add primary_product_type to designs

Revision ID: 011
Revises: 010
"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("designs", sa.Column("primary_product_type", sa.String(30), nullable=True, server_default="tshirt"))


def downgrade() -> None:
    op.drop_column("designs", "primary_product_type")
