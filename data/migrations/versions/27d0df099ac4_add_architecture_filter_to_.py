"""add architecture filter to repomirrorconfig

Revision ID: 27d0df099ac4
Revises: 9307c3d604b4
Create Date: 2026-01-14 14:40:55.461972

"""

# revision identifiers, used by Alembic.
revision = '27d0df099ac4'
down_revision = '9307c3d604b4'

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.add_column(
        "repomirrorconfig",
        sa.Column("architecture_filter", sa.Text(), nullable=True),
    )


def downgrade(op, tables, tester):
    op.drop_column("repomirrorconfig", "architecture_filter")
