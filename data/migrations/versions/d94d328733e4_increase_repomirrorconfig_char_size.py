"""Increase repomirrorconfig char size

Revision ID: d94d328733e4
Revises: b43b44996c26
Create Date: 2022-04-12 14:16:07.660766

"""

# revision identifiers, used by Alembic.
revision = "d94d328733e4"
down_revision = "b43b44996c26"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    with op.batch_alter_table("repomirrorconfig") as batch_op:
        batch_op.alter_column(
            "external_registry_username",
            type_=sa.String(length=4096),
            nullable=True,
        )
        batch_op.alter_column(
            "external_registry_password",
            type_=sa.String(length=4096),
            nullable=True,
        )


def downgrade(op, tables, tester):
    with op.batch_alter_table("repomirrorconfig") as batch_op:
        batch_op.alter_column(
            "external_registry_username",
            type_=sa.String(length=2048),
            nullable=True,
        )
        batch_op.alter_column(
            "external_registry_password",
            type_=sa.String(length=2048),
            nullable=True,
        )
