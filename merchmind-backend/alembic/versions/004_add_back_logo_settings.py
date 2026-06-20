"""Add back_logo_enabled and back_logo_url to settings

Revision ID: 004
Revises: 003
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"


def upgrade():
    op.add_column("settings", sa.Column("back_logo_enabled", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("settings", sa.Column("back_logo_url", sa.Text(), nullable=True))
    op.add_column("settings", sa.Column("back_logo_products", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("settings", "back_logo_products")
    op.drop_column("settings", "back_logo_url")
    op.drop_column("settings", "back_logo_enabled")
