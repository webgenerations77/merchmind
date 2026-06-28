"""Trend approval gate: add approval_status/selected_generator to trends,
pending_approval to batch_status, and target_store to products.

Revision ID: 023
Revises: 022
"""
from alembic import op
import sqlalchemy as sa

revision = "023"
down_revision = "022"


def upgrade():
    conn = op.get_bind()

    # ALTER TYPE ADD VALUE must run outside a transaction block
    conn.execute(sa.text("COMMIT"))
    conn.execute(sa.text("ALTER TYPE batch_status ADD VALUE IF NOT EXISTS 'pending_approval'"))
    conn.execute(sa.text("BEGIN"))

    # Trend approval columns
    conn.execute(sa.text(
        "ALTER TABLE trends ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) NOT NULL DEFAULT 'pending_review'"
    ))
    conn.execute(sa.text(
        "ALTER TABLE trends ADD COLUMN IF NOT EXISTS selected_generator VARCHAR(50)"
    ))
    conn.execute(sa.text(
        "ALTER TABLE trends ADD COLUMN IF NOT EXISTS proposed_archetype VARCHAR(50)"
    ))

    # Store selection on products
    conn.execute(sa.text(
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS target_store VARCHAR(10) DEFAULT 'store_1'"
    ))


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE products DROP COLUMN IF EXISTS target_store"))
    conn.execute(sa.text("ALTER TABLE trends DROP COLUMN IF EXISTS proposed_archetype"))
    conn.execute(sa.text("ALTER TABLE trends DROP COLUMN IF EXISTS selected_generator"))
    conn.execute(sa.text("ALTER TABLE trends DROP COLUMN IF EXISTS approval_status"))
