"""add manifest creation date

Revision ID: d241e4f6e5bd
Revises: 36cd2b747a08
Create Date: 2024-03-27 09:42:51.183411

"""

# revision identifiers, used by Alembic.
revision = "d241e4f6e5bd"
down_revision = "36cd2b747a08"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.add_column("manifest", sa.Column("created", sa.BigInteger(), nullable=True))


def downgrade(op, tables, tester):
    op.drop_column("manifest", "created")
