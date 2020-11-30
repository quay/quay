"""
Create new notification type.

Revision ID: 94836b099894
Revises: faf752bd2e0a
Create Date: 2016-11-30 10:29:51.519278
"""

# revision identifiers, used by Alembic.
revision = "94836b099894"
down_revision = "faf752bd2e0a"


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.externalnotificationevent,
        [
            {"name": "build_cancelled"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.externalnotificationevent.delete().where(
            tables.externalnotificationevent.c.name == op.inline_literal("build_cancelled")
        )
    )
