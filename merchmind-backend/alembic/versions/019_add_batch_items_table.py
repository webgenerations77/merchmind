"""Add batch_items table for per-item pipeline tracking

Revision ID: 019
Revises: 018
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "batch_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("batch_id", UUID(as_uuid=True), sa.ForeignKey("batches.id"), nullable=False, index=True),
        sa.Column("trend_id", UUID(as_uuid=True), sa.ForeignKey("trends.id"), nullable=True),
        sa.Column("design_id", UUID(as_uuid=True), sa.ForeignKey("designs.id"), nullable=True),
        sa.Column("concept_name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("failed_step", sa.String(50), nullable=True),
        sa.Column("error_summary", sa.String(500), nullable=True),
        sa.Column("error_detail", sa.Text, nullable=True),
        sa.Column("product_types", JSONB, server_default="[]"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("batch_items")
