"""
add notification number of failures column.

Revision ID: dc4af11a5f90
Revises: 53e2ac668296
Create Date: 2017-05-16 17:24:02.630365
"""

# revision identifiers, used by Alembic.
revision = "dc4af11a5f90"
down_revision = "53e2ac668296"

import sqlalchemy as sa


def upgrade(op, tables, tester):
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


def downgrade(op, tables, tester):
    op.drop_column("repositorynotification", "number_of_failures")
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name == op.inline_literal("reset_repo_notification")
        )
    )
