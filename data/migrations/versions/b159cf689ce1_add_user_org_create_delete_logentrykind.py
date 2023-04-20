"""add user/org create delete logentrykind

Revision ID: b159cf689ce1
Revises: b2d1e4b95fc2
Create Date: 2023-04-20 10:25:26.068215

"""

# revision identifiers, used by Alembic.
revision = 'b159cf689ce1'
down_revision = 'b2d1e4b95fc2'

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "create_user"},
            {"name": "create_org"},
            {"name": "delete_user"},
            {"name": "delete_org"},
            {"name": "change_org_email"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.name
            == op.inline_literal("create_user") | tables.logentrykind.name
            == op.inline_literal("create_org") | tables.logentrykind.name
            == op.inline_literal("delete_user") | tables.logentrykind.name
            == op.inline_literal("delete_org") | tables.logentrykind.name
            == op.inline_literal("change_org_email")
        )
    )
