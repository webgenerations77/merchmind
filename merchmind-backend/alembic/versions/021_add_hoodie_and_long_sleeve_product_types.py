"""Add hoodie and long_sleeve to product_type enum

Revision ID: 021
Revises: 020
"""
from alembic import op
import sqlalchemy as sa

revision = "021"
down_revision = "020"


def upgrade():
    # ALTER TYPE ADD VALUE must run outside a transaction block on some PostgreSQL versions.
    conn = op.get_bind()
    conn.execute(sa.text("COMMIT"))
    conn.execute(sa.text("ALTER TYPE product_type ADD VALUE IF NOT EXISTS 'hoodie'"))
    conn.execute(sa.text("ALTER TYPE product_type ADD VALUE IF NOT EXISTS 'long_sleeve'"))
    conn.execute(sa.text("BEGIN"))


def downgrade():
    pass
