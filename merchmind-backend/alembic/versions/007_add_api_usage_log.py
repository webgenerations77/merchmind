"""Add api_usage_logs table for tracking API costs

Revision ID: 007
Revises: 006
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "007"
down_revision = "006"


def upgrade():
    op.create_table(
        "api_usage_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("service", sa.String(50), nullable=False),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("input_tokens", sa.Integer(), default=0),
        sa.Column("output_tokens", sa.Integer(), default=0),
        sa.Column("estimated_cost", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("design_id", UUID(as_uuid=True), nullable=True),
        sa.Column("batch_id", UUID(as_uuid=True), nullable=True),
        sa.Column("collection_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_api_usage_created", "api_usage_logs", ["created_at"])
    op.create_index("ix_api_usage_service", "api_usage_logs", ["service"])


def downgrade():
    op.drop_table("api_usage_logs")
