"""add quantity field to orgRhSkus

Revision ID: 41d15c93c299
Revises: 3f8e3657bb67
Create Date: 2024-01-24 11:19:19.095256

"""

# revision identifiers, used by Alembic.
revision = "41d15c93c299"
down_revision = "3f8e3657bb67"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.add_column("organizationrhskus", sa.Column("quantity", sa.Integer(), nullable=True))


def downgrade(op, tables, tester):
    with op.batch_alter_table("organizationrhskus") as batch_op:
        batch_op.drop_column("quantity")
