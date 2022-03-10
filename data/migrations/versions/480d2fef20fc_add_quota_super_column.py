"""add quota super column

Revision ID: 480d2fef20fc
Revises: e9f3e4dbb979
Create Date: 2022-03-10 12:48:12.686943

"""

# revision identifiers, used by Alembic.
revision = '480d2fef20fc'
down_revision = 'e9f3e4dbb979'

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.add_column(
        "userorganizationquota", sa.Column("set_by_super", sa.Boolean, nullable=False, default=0)
    )


def downgrade(op, tables, tester):
    op.drop_column("userorganizationquota", "set_by_super")
