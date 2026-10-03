"""add poc_rollback_demo table

Revision ID: a1b2c3d4e5f7
Revises: 15f06d00c4b3
Create Date: 2026-03-16 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f7"
down_revision = "15f06d00c4b3"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "poc_rollback_demo",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_poc_rollback_demo")),
    )
    op.create_index(
        "poc_rollback_demo_name",
        "poc_rollback_demo",
        ["name"],
        unique=True,
    )


def downgrade(op, tables, tester):
    op.drop_index("poc_rollback_demo_name", table_name="poc_rollback_demo")
    op.drop_table("poc_rollback_demo")
