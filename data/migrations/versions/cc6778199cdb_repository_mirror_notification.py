"""repository mirror notification

Revision ID: cc6778199cdb
Revises: c059b952ed76
Create Date: 2019-10-03 17:41:23.316914

"""

# revision identifiers, used by Alembic.
revision = "cc6778199cdb"
down_revision = "c059b952ed76"

from alembic import op as original_op
from data.migrations.progress import ProgressWrapper
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


def upgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)

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


def downgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)

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
