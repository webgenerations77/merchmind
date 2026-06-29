"""Add selected_color + color_mockups to products.

Revision ID: 026
Revises: 025
"""
from alembic import op
import sqlalchemy as sa

revision = "026"
down_revision = "025"


def upgrade():
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE products ADD COLUMN IF NOT EXISTS selected_color VARCHAR(64)"))
    conn.execute(sa.text("ALTER TABLE products ADD COLUMN IF NOT EXISTS color_mockups JSONB DEFAULT '{}'::jsonb"))


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE products DROP COLUMN IF EXISTS color_mockups"))
    conn.execute(sa.text("ALTER TABLE products DROP COLUMN IF EXISTS selected_color"))
