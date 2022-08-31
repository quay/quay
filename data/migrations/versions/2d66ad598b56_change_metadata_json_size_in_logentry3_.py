"""
Change metadata_json size in logentry3 table for MySQL

Revision ID: 2d66ad598b56
Revises: d94d328733e4
Create Date: 2022-08-31 15:44:12.121324

"""

# revision identifiers, used by Alembic.
revision = "2d66ad598b56"
down_revision = "d94d328733e4"

import sqlalchemy as sa
from sqlalchemy.dialects import mysql


def upgrade(op, tables, tester):
    bind = op.get_bind()
    if bind.engine.name == "mysql":
        op.alter_column("logentry3", "metadata_json", nullable=False, type_=mysql.MEDIUMTEXT())
    else:
        pass


def downgrade(op, tables, tester):
    bind = op.get_bind()
    if bind.engine.name == "mysql":
        op.alter_column("logentry3", "metadata_json", type=sa.Text())
    else:
        pass
