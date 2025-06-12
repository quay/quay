"""Add skopeo timeout to mirroring config

Revision ID: 1623f40582ed
Revises: e8ed3fb547da
Create Date: 2025-06-12 13:26:26.010165

"""

# revision identifiers, used by Alembic.
revision = "1623f40582ed"
down_revision = "e8ed3fb547da"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.add_column(
        "repomirrorconfig",
        sa.Column("skopeo_timeout", sa.BigInteger(), nullable=False, server_default="300"),
    )


def downgrade(op, tables, tester):
    op.drop_column("repomirrorconfig", "skopeo_timeout")
