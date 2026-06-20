"""Add flux_schnell to image_api enum

Revision ID: 002
Revises: 001
"""
from alembic import op

revision = "002"
down_revision = "001"


def upgrade():
    op.execute("ALTER TYPE image_api ADD VALUE IF NOT EXISTS 'flux_schnell'")


def downgrade():
    pass
