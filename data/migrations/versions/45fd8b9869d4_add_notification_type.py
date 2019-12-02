"""add_notification_type

Revision ID: 45fd8b9869d4
Revises: 94836b099894
Create Date: 2016-12-01 12:02:19.724528

"""

# revision identifiers, used by Alembic.
revision = "45fd8b9869d4"
down_revision = "94836b099894"

from alembic import op as original_op
from data.migrations.progress import ProgressWrapper


def upgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)
    op.bulk_insert(tables.notificationkind, [{"name": "build_cancelled"},])


def downgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)
    op.execute(
        tables.notificationkind.delete().where(
            tables.notificationkind.c.name == op.inline_literal("build_cancelled")
        )
    )
