"""add build triggers' logentrykind

Revision ID: b2d1e4b95fc2
Revises: 7bca88923f2c
Create Date: 2022-12-15 10:49:28.895549

"""

# revision identifiers, used by Alembic.
revision = "b2d1e4b95fc2"
down_revision = "7bca88923f2c"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "start_build_trigger"},
            {"name": "cancel_build"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.name
            == op.inline_literal("start_build_trigger") | tables.logentrykind.name
            == op.inline_literal("cancel_build")
        )
    )
