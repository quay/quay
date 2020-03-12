"""
Add user location field.

Revision ID: cbc8177760d9
Revises: 7367229b38d9
Create Date: 2018-02-02 17:39:16.589623
"""

# revision identifiers, used by Alembic.
revision = "cbc8177760d9"
down_revision = "7367229b38d9"

import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from util.migrate import UTF8CharField


def upgrade(op, tables, tester):
    op.add_column("user", sa.Column("location", UTF8CharField(length=255), nullable=True))

    # ### population of test data ### #
    tester.populate_column("user", "location", tester.TestDataType.UTF8Char)
    # ### end population of test data ### #


def downgrade(op, tables, tester):
    op.drop_column("user", "location")
