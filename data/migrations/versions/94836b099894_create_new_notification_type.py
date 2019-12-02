"""Create new notification type

Revision ID: 94836b099894
Revises: faf752bd2e0a
Create Date: 2016-11-30 10:29:51.519278

"""

# revision identifiers, used by Alembic.
revision = "94836b099894"
down_revision = "faf752bd2e0a"

from alembic import op as original_op
from data.migrations.progress import ProgressWrapper


def upgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)
    op.bulk_insert(tables.externalnotificationevent, [{"name": "build_cancelled"},])


def downgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)
    op.execute(
        tables.externalnotificationevent.delete().where(
            tables.externalnotificationevent.c.name == op.inline_literal("build_cancelled")
        )
    )
