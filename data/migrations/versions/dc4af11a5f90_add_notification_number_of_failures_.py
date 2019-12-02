"""add notification number of failures column

Revision ID: dc4af11a5f90
Revises: 53e2ac668296
Create Date: 2017-05-16 17:24:02.630365

"""

# revision identifiers, used by Alembic.
revision = "dc4af11a5f90"
down_revision = "53e2ac668296"

import sqlalchemy as sa
from alembic import op as original_op
from data.migrations.progress import ProgressWrapper


def upgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)
    op.add_column(
        "repositorynotification",
        sa.Column("number_of_failures", sa.Integer(), nullable=False, server_default="0"),
    )
    op.bulk_insert(tables.logentrykind, [{"name": "reset_repo_notification"},])

    # ### population of test data ### #
    tester.populate_column(
        "repositorynotification", "number_of_failures", tester.TestDataType.Integer
    )
    # ### end population of test data ### #


def downgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)
    op.drop_column("repositorynotification", "number_of_failures")
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name == op.inline_literal("reset_repo_notification")
        )
    )
