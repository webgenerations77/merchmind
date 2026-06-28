"""Add generation_failed to design_status enum

Revision ID: 024
Revises: 023
"""
from alembic import op
import sqlalchemy as sa

revision = "024"
down_revision = "023"


def upgrade():
    # ALTER TYPE ADD VALUE must run outside a transaction block on some PostgreSQL versions.
    conn = op.get_bind()
    conn.execute(sa.text("COMMIT"))
    conn.execute(sa.text("ALTER TYPE design_status ADD VALUE IF NOT EXISTS 'generation_failed'"))
    conn.execute(sa.text("BEGIN"))


def downgrade():
    pass
