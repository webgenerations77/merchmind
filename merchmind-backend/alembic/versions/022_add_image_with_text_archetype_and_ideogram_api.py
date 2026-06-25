"""Add image_with_text to design_archetype enum and ideogram to image_api enum

Revision ID: 022
Revises: 021
"""
from alembic import op

revision = "022"
down_revision = "021"


def upgrade():
    op.execute("ALTER TYPE design_archetype ADD VALUE IF NOT EXISTS 'image_with_text'")
    op.execute("ALTER TYPE image_api ADD VALUE IF NOT EXISTS 'ideogram'")


def downgrade():
    pass
