"""
Change manifest_bytes to a UTF8 text field.

Revision ID: 654e6df88b71
Revises: eafdeadcebc7
Create Date: 2018-08-15 09:58:46.109277
"""

# revision identifiers, used by Alembic.
revision = "654e6df88b71"
down_revision = "eafdeadcebc7"

import sqlalchemy as sa

from util.migrate import UTF8LongText


def upgrade(op, tables, tester):
    op.alter_column("manifest", "manifest_bytes", existing_type=sa.Text(), type_=UTF8LongText())


def downgrade(op, tables, tester):
    op.alter_column("manifest", "manifest_bytes", existing_type=UTF8LongText(), type_=sa.Text())
