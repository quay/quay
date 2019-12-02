"""Cleanup old robots

Revision ID: 5b7503aada1b
Revises: 224ce4c72c2f
Create Date: 2018-05-09 17:18:52.230504

"""

# revision identifiers, used by Alembic.
revision = "5b7503aada1b"
down_revision = "224ce4c72c2f"

from alembic import op as original_op
from data.migrations.progress import ProgressWrapper
import sqlalchemy as sa

from util.migrate.cleanup_old_robots import cleanup_old_robots


def upgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)
    cleanup_old_robots()


def downgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)
    # Nothing to do.
    pass
