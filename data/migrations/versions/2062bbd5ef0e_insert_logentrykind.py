"""insert logentrykind

Revision ID: 2062bbd5ef0e
Revises: 222debc16e18
Create Date: 2023-10-04 15:40:15.341514

"""

# revision identifiers, used by Alembic.
revision = "2062bbd5ef0e"
down_revision = "222debc16e18"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "autoprune_tag_delete"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.name == op.inline_literal("autoprune_tag_delete")
        )
    )
