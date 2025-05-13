"""alter manifestblob id

Revision ID: e8ed3fb547da
Revises: 3634f2df3c5b
Create Date: 2025-05-13 09:45:39.152681

"""

# revision identifiers, used by Alembic.
revision = "e8ed3fb547da"
down_revision = "3634f2df3c5b"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.alter_column(
        "manifestblob", "id", existing_type=sa.Integer, type_=sa.BigInteger, existing_nullable=False
    )


def downgrade(op, tables, tester):
    op.alter_column(
        "manifestblob", "id", existing_type=sa.BigInteger, type_=sa.Integer, existing_nullable=False
    )
