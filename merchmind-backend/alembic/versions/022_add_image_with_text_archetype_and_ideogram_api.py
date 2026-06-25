"""Add image_with_text to design_archetype enum and ideogram to image_api enum

Revision ID: 022
Revises: 021
"""
from alembic import op
import sqlalchemy as sa

revision = "022"
down_revision = "021"


def upgrade():
    # ALTER TYPE ADD VALUE must run outside a transaction block on some PostgreSQL versions.
    conn = op.get_bind()
    conn.execute(sa.text("COMMIT"))
    conn.execute(sa.text("ALTER TYPE design_archetype ADD VALUE IF NOT EXISTS 'image_with_text'"))
    conn.execute(sa.text("ALTER TYPE image_api ADD VALUE IF NOT EXISTS 'ideogram'"))
    conn.execute(sa.text("BEGIN"))


def downgrade():
    pass
