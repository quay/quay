"""
Make BlodUpload byte_count not nullable.

Revision ID: 152edccba18c
Revises: c91c564aad34
Create Date: 2018-02-23 12:41:25.571835
"""

# revision identifiers, used by Alembic.
revision = "152edccba18c"
down_revision = "c91c564aad34"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.alter_column("blobupload", "byte_count", existing_type=sa.BigInteger(), nullable=False)


def downgrade(op, tables, tester):
    op.alter_column("blobupload", "byte_count", existing_type=sa.BigInteger(), nullable=True)
