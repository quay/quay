"""change removed_tag_expiration_s to BIGINT

Revision ID: 46980ea2dde5
Revises: 8cf90670bf38
Create Date: 2023-06-04 11:14:26.150812

"""

# revision identifiers, used by Alembic.
revision = "46980ea2dde5"
down_revision = "8cf90670bf38"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    # Alter the column to use BIGINT data type
    with op.batch_alter_table("user") as batch_op:
        batch_op.alter_column("removed_tag_expiration_s", type_=sa.BigInteger)


def downgrade(op, tables, tester):
    # Alter the column to use INT data type, this might fail if there are already values that are bigger than INT but we do not intend to support downgrades anyway
    with op.batch_alter_table("user") as batch_op:
        batch_op.alter_column("removed_tag_expiration_s", type_=sa.Integer)
