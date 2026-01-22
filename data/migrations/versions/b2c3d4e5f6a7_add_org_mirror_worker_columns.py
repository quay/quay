"""add org mirror worker columns

Revision ID: b2c3d4e5f6a7
Revises: 285f36ce97fd
Create Date: 2026-01-22 10:00:00.000000

Adds sync retry columns to orgmirrorrepository and architecture filter to orgmirrorconfig.
"""

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "285f36ce97fd"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    # Add sync_retries_remaining column to orgmirrorrepository
    op.add_column(
        "orgmirrorrepository",
        sa.Column("sync_retries_remaining", sa.Integer(), nullable=False, server_default="3"),
    )

    # Add sync_transaction_id column to orgmirrorrepository
    op.add_column(
        "orgmirrorrepository",
        sa.Column("sync_transaction_id", sa.String(length=36), nullable=True),
    )

    # Update test data
    tester.populate_column(
        "orgmirrorrepository",
        "sync_retries_remaining",
        tester.TestDataType.Integer,
    )

    tester.populate_column(
        "orgmirrorrepository",
        "sync_transaction_id",
        tester.TestDataType.String,
    )

    # Add architecture_filter column to orgmirrorconfig
    # Stores a JSON list of architectures to mirror (e.g., ["amd64", "arm64"])
    # Empty list means mirror all architectures
    op.add_column(
        "orgmirrorconfig",
        sa.Column("architecture_filter", sa.Text(), nullable=False, server_default="[]"),
    )

    tester.populate_column(
        "orgmirrorconfig",
        "architecture_filter",
        tester.TestDataType.JSON,
    )


def downgrade(op, tables, tester):
    op.drop_column("orgmirrorconfig", "architecture_filter")
    op.drop_column("orgmirrorrepository", "sync_transaction_id")
    op.drop_column("orgmirrorrepository", "sync_retries_remaining")
