"""increase proxy cache config creds max len

Revision ID: b43b44996c26
Revises: 10d34e6536f8
Create Date: 2022-04-12 09:14:00.910916

"""

# revision identifiers, used by Alembic.
revision = "b43b44996c26"
down_revision = "10d34e6536f8"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    with op.batch_alter_table("proxycacheconfig") as batch_op:
        batch_op.alter_column(
            "upstream_registry_username",
            type_=sa.String(length=4096),
            nullable=True,
        )
        batch_op.alter_column(
            "upstream_registry_password",
            type_=sa.String(length=4096),
            nullable=True,
        )


def downgrade(op, tables, tester):
    with op.batch_alter_table("proxycacheconfig") as batch_op:
        batch_op.alter_column(
            "upstream_registry_username",
            type_=sa.String(length=2048),
            nullable=True,
        )
        batch_op.alter_column(
            "upstream_registry_password",
            type_=sa.String(length=2048),
            nullable=True,
        )
