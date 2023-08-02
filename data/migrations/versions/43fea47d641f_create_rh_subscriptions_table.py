"""create RH subscriptions table

Revision ID: 43fea47d641f
Revises: b2d1e4b95fc2
Create Date: 2023-03-15 11:17:35.991320

"""

# revision identifiers, used by Alembic.
revision = "43fea47d641f"
down_revision = "a648ab200ab7"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "redhatsubscriptions",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("account_number", sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_redhatsubscriptions")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_redhatsubscriptions")),
    )


def downgrade(op, tables, tester):
    op.drop_table("redhatsubscriptions")
