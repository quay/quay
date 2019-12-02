"""Add user location field

Revision ID: cbc8177760d9
Revises: 7367229b38d9
Create Date: 2018-02-02 17:39:16.589623

"""

# revision identifiers, used by Alembic.
revision = "cbc8177760d9"
down_revision = "7367229b38d9"

from alembic import op as original_op
from data.migrations.progress import ProgressWrapper
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from util.migrate import UTF8CharField


def upgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)
    op.add_column("user", sa.Column("location", UTF8CharField(length=255), nullable=True))

    # ### population of test data ### #
    tester.populate_column("user", "location", tester.TestDataType.UTF8Char)
    # ### end population of test data ### #


def downgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)
    op.drop_column("user", "location")
