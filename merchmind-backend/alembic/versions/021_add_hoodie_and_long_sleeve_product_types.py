"""Add hoodie and long_sleeve to product_type enum

Revision ID: 021
Revises: 020
"""
from alembic import op

revision = "021"
down_revision = "020"


def upgrade():
    op.execute("ALTER TYPE product_type ADD VALUE IF NOT EXISTS 'hoodie'")
    op.execute("ALTER TYPE product_type ADD VALUE IF NOT EXISTS 'long_sleeve'")


def downgrade():
    pass
