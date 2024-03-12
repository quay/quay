"""team sync logs

Revision ID: 36cd2b747a08
Revises: cead4183265c
Create Date: 2024-03-12 14:55:19.431028

"""

# revision identifiers, used by Alembic.
revision = "36cd2b747a08"
down_revision = "cead4183265c"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "enable_team_sync"},
            {"name": "disable_team_sync"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name
            == op.inline_literal("enable_team_sync") | tables.logentrykind.c.name
            == op.inline_literal("disable_team_sync") | tables.logentrykind.c.name
        )
    )
