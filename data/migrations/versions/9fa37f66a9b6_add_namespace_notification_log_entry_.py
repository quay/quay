"""add_namespace_notification_log_entry_kinds

Revision ID: 9fa37f66a9b6
Revises: 6715e4719375
Create Date: 2026-06-15 05:51:03.893282

"""

# revision identifiers, used by Alembic.
revision = '9fa37f66a9b6'
down_revision = '6715e4719375'

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "create_namespace_notification"},
            {"name": "delete_namespace_notification"},
            {"name": "reset_namespace_notification"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name.in_(
                [
                    "create_namespace_notification",
                    "delete_namespace_notification",
                    "reset_namespace_notification",
                ]
            )
        )
    )
