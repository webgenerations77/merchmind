"""Add collections table and collection_id to designs

Revision ID: 005
Revises: 004
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "005"
down_revision = "004"


def upgrade():
    op.create_table(
        "collections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("style_guide", JSONB, nullable=False, server_default="{}"),
        sa.Column("max_designs", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("status", sa.Enum("draft", "generating", "ready", "published", name="collection_status"), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.add_column("designs", sa.Column("collection_id", UUID(as_uuid=True), sa.ForeignKey("collections.id"), nullable=True))


def downgrade():
    op.drop_column("designs", "collection_id")
    op.drop_table("collections")
    op.execute("DROP TYPE IF EXISTS collection_status")
