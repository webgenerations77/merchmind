"""Add firecrawl to trend_source enum

Revision ID: 025
Revises: 024
"""
from alembic import op
import sqlalchemy as sa

revision = "025"
down_revision = "024"


def upgrade():
    # ALTER TYPE ADD VALUE must run outside a transaction block on some PostgreSQL versions.
    conn = op.get_bind()
    conn.execute(sa.text("COMMIT"))
    conn.execute(sa.text("ALTER TYPE trend_source ADD VALUE IF NOT EXISTS 'firecrawl'"))
    conn.execute(sa.text("BEGIN"))


def downgrade():
    pass
