"""Add log event kind for federated robot

Revision ID: 9085e82074f2
Revises: a32e17bfad20
Create Date: 2024-09-09 15:49:24.911854

"""

# revision identifiers, used by Alembic.
revision = "9085e82074f2"
down_revision = "ba263f9be4a6"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "create_robot_federation"},
            {"name": "delete_robot_federation"},
            {"name": "federated_robot_token_exchange"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name
            == op.inline_literal("create_robot_federation") | tables.logentrykind.c.name
            == op.inline_literal("delete_robot_federation") | tables.logentrykind.c.name
            == op.inline_literal("federated_robot_token_exchange")
        )
    )
