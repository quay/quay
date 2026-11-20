"""auto prune policy audit logs

Revision ID: 8d47693829a0
Revises: 2062bbd5ef0e
Create Date: 2023-10-23 14:34:38.908240

"""

# revision identifiers, used by Alembic.
revision = "8d47693829a0"
down_revision = "2062bbd5ef0e"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "create_namespace_autoprune_policy"},
            {"name": "update_namespace_autoprune_policy"},
            {"name": "delete_namespace_autoprune_policy"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name.in_(
                [
                    "create_namespace_autoprune_policy",
                    "update_namespace_autoprune_policy",
                    "delete_namespace_autoprune_policy",
                ]
            )
        )
    )
