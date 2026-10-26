"""add oauth token display name

Revision ID: b30800b1d271
Revises: d064a4f00d4a
Create Date: 2026-07-09 17:12:54.070165

"""

# revision identifiers, used by Alembic.
revision = "b30800b1d271"
down_revision = "d064a4f00d4a"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.add_column(
        "oauthaccesstoken", sa.Column("display_name", sa.String(length=255), nullable=True)
    )
    tester.populate_column("oauthaccesstoken", "display_name", tester.TestDataType.String)


def downgrade(op, tables, tester):
    with op.batch_alter_table("oauthaccesstoken") as batch_op:
        batch_op.drop_column("display_name")
