"""add error_count column to manifestsecuritystatus

Revision ID: f77bb557a345
Revises: c3d4e5f6a7b8
Create Date: 2026-06-16 13:44:31.119113

"""

# revision identifiers, used by Alembic.
revision = "f77bb557a345"
down_revision = "d064a4f00d4a"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.add_column(
        "manifestsecuritystatus",
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade(op, tables, tester):
    op.drop_column("manifestsecuritystatus", "error_count")
