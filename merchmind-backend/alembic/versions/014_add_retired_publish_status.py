"""Add retired to publish_status enum

Revision ID: 014
Revises: 013
"""
from alembic import op

revision = "014"
down_revision = "013"


def upgrade():
    op.execute("ALTER TYPE publish_status ADD VALUE IF NOT EXISTS 'retired'")


def downgrade():
    pass
