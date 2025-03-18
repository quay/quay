"""Add skopeo timeout to mirroring config

Revision ID: a52c7684f140
Revises: 3634f2df3c5b
Create Date: 2025-03-18 18:15:05.053141

"""

# revision identifiers, used by Alembic.
revision = "a52c7684f140"
down_revision = "3634f2df3c5b"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.add_column(
        "repomirrorconfig",
        sa.Column("skopeo_timeout", sa.BigInteger(), nullable=False, server_default="300"),
    )


def downgrade(op, tables, tester):
    op.drop_column("repomirrorconfig", "skopeo_timeout")
