"""add org_mirror_repo_creation_failed log kind

Revision ID: b1c2d3e4f5a6
Revises: b2c3d4e5f6a7
Create Date: 2026-01-28 10:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5a6"
down_revision = "b2c3d4e5f6a7"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "org_mirror_repo_creation_failed"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name == op.inline_literal("org_mirror_repo_creation_failed")
        )
    )
