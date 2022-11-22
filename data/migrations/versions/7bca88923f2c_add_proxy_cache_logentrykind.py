"""add proxy cache logentrykind

Revision ID: 7bca88923f2c
Revises: 2d66ad598b56
Create Date: 2022-11-10 11:16:51.982538

"""

# revision identifiers, used by Alembic.
revision = "7bca88923f2c"
down_revision = "2d66ad598b56"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "create_proxy_cache_config"},
            {"name": "delete_proxy_cache_config"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.name
            == op.inline_literal("create_proxy_cache_config") | tables.logentrykind.name
            == op.inline_literal("delete_proxy_cache_config")
        )
    )
