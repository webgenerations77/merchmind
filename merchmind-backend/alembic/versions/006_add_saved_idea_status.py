"""Add 'saved' to idea_status enum

Revision ID: 006
Revises: 005
"""
from alembic import op

revision = "006"
down_revision = "005"


def upgrade():
    op.execute("ALTER TYPE idea_status ADD VALUE IF NOT EXISTS 'saved'")


def downgrade():
    pass
