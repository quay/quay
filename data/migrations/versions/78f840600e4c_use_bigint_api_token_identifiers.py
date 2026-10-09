"""use bigint API token identifiers

Revision ID: 78f840600e4c
Revises: 3cb9c1acb681
Create Date: 2026-10-09 17:33:36.215842

"""

# revision identifiers, used by Alembic.
revision = "78f840600e4c"
down_revision = "3cb9c1acb681"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    with op.batch_alter_table("apitoken") as batch_op:
        batch_op.alter_column("id", nullable=False, autoincrement=True, type_=sa.BigInteger())

    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER SEQUENCE apitoken_id_seq AS BIGINT")
        op.execute("ALTER SEQUENCE apitoken_id_seq MAXVALUE 9223372036854775807")


def downgrade(op, tables, tester):
    with op.batch_alter_table("apitoken") as batch_op:
        batch_op.alter_column("id", nullable=False, autoincrement=True, type_=sa.Integer())

    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER SEQUENCE apitoken_id_seq AS INTEGER")
        op.execute("ALTER SEQUENCE apitoken_id_seq MAXVALUE 2147483647")
