"""
repository mirror notification.

Revision ID: cc6778199cdb
Revises: c059b952ed76
Create Date: 2019-10-03 17:41:23.316914
"""

# revision identifiers, used by Alembic.
revision = "cc6778199cdb"
down_revision = "c059b952ed76"

import sqlalchemy as sa
from sqlalchemy.dialects import mysql


def upgrade(op, tables, tester):

    op.bulk_insert(
        tables.notificationkind,
        [
            {"name": "repo_mirror_sync_started"},
            {"name": "repo_mirror_sync_success"},
            {"name": "repo_mirror_sync_failed"},
        ],
    )
    op.bulk_insert(
        tables.externalnotificationevent,
        [
            {"name": "repo_mirror_sync_started"},
            {"name": "repo_mirror_sync_success"},
            {"name": "repo_mirror_sync_failed"},
        ],
    )


def downgrade(op, tables, tester):

    op.execute(
        tables.notificationkind.delete().where(
            tables.notificationkind.c.name == op.inline_literal("repo_mirror_sync_started")
        )
    )
    op.execute(
        tables.notificationkind.delete().where(
            tables.notificationkind.c.name == op.inline_literal("repo_mirror_sync_success")
        )
    )
    op.execute(
        tables.notificationkind.delete().where(
            tables.notificationkind.c.name == op.inline_literal("repo_mirror_sync_failed")
        )
    )

    op.execute(
        tables.externalnotificationevent.delete().where(
            tables.externalnotificationevent.c.name == op.inline_literal("repo_mirror_sync_started")
        )
    )
    op.execute(
        tables.externalnotificationevent.delete().where(
            tables.externalnotificationevent.c.name == op.inline_literal("repo_mirror_sync_success")
        )
    )
    op.execute(
        tables.externalnotificationevent.delete().where(
            tables.externalnotificationevent.c.name == op.inline_literal("repo_mirror_sync_failed")
        )
    )
