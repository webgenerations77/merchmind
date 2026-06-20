"""Add custom_ideas table and make design foreign keys nullable

Revision ID: 003
Revises: 002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "003"
down_revision = "002"


def upgrade():
    op.create_table(
        "custom_ideas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("input_text", sa.Text, nullable=False),
        sa.Column("source", sa.String(50), default="drews_mind"),
        sa.Column("design_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Enum("pending", "generating", "complete", "failed", name="idea_status", create_type=True), nullable=False, server_default="pending"),
        sa.Column("preferences", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.alter_column("designs", "trend_id", nullable=True)
    op.alter_column("designs", "batch_id", nullable=True)


def downgrade():
    op.alter_column("designs", "batch_id", nullable=False)
    op.alter_column("designs", "trend_id", nullable=False)
    op.drop_table("custom_ideas")
    op.execute("DROP TYPE IF EXISTS idea_status")
