"""
Drop checksum on ImageStorage.

Revision ID: c91c564aad34
Revises: 152bb29a1bb3
Create Date: 2018-02-21 12:17:52.405644
"""

# revision identifiers, used by Alembic.
revision = "c91c564aad34"
down_revision = "152bb29a1bb3"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.drop_column("imagestorage", "checksum")


def downgrade(op, tables, tester):
    op.add_column("imagestorage", sa.Column("checksum", sa.String(length=255), nullable=True))
