"""Add merch_drops table and drop_id FK on products

Revision ID: 020
Revises: 019
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade():
    drop_status = sa.Enum("scheduled", "in_progress", "published", "failed", name="drop_status")
    drop_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "merch_drops",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", drop_status, nullable=False, server_default="scheduled"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "drop_marketing_assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("drop_id", UUID(as_uuid=True), sa.ForeignKey("merch_drops.id"), nullable=False, index=True),
        sa.Column("channel", sa.Enum("instagram", "tiktok", "pinterest", "email", "blog", name="marketing_channel", create_type=False), nullable=False),
        sa.Column("content", JSONB, server_default="{}"),
        sa.Column("status", sa.Enum("pending", "approved", "scheduled", "posted", "failed", name="asset_status", create_type=False), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.add_column(
        "products",
        sa.Column("drop_id", UUID(as_uuid=True), sa.ForeignKey("merch_drops.id"), nullable=True),
    )
    op.create_index("ix_products_drop_id", "products", ["drop_id"])


def downgrade():
    op.drop_index("ix_products_drop_id", table_name="products")
    op.drop_column("products", "drop_id")
    op.drop_table("drop_marketing_assets")
    op.drop_table("merch_drops")
    sa.Enum(name="drop_status").drop(op.get_bind(), checkfirst=True)
