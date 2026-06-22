"""Add marketing_generation_enabled and social_links to settings

Revision ID: 018
Revises: 017
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "settings",
        sa.Column("marketing_generation_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "settings",
        sa.Column(
            "social_links",
            JSONB,
            nullable=True,
            server_default='{"instagram_url": "", "tiktok_url": "", "pinterest_url": "", "facebook_url": ""}',
        ),
    )


def downgrade() -> None:
    op.drop_column("settings", "social_links")
    op.drop_column("settings", "marketing_generation_enabled")
