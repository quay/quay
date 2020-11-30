"""
add_notification_type.

Revision ID: 45fd8b9869d4
Revises: 94836b099894
Create Date: 2016-12-01 12:02:19.724528
"""

# revision identifiers, used by Alembic.
revision = "45fd8b9869d4"
down_revision = "94836b099894"


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.notificationkind,
        [
            {"name": "build_cancelled"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.notificationkind.delete().where(
            tables.notificationkind.c.name == op.inline_literal("build_cancelled")
        )
    )
