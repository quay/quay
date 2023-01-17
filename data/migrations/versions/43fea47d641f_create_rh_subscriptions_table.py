"""create RH subscriptions table

Revision ID: 43fea47d641f
Revises: b2d1e4b95fc2
Create Date: 2023-03-15 11:17:35.991320

"""

# revision identifiers, used by Alembic.
revision = "43fea47d641f"
down_revision = "b2d1e4b95fc2"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "redhatsubscriptions",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("subscription_id", sa.Integer, unique=True),
        sa.Column("account_number", sa.Integer, nullable=False),
        sa.Column("subscription_end_date", sa.DateTime),
        sa.Column("sku_id", sa.String(length=9)),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_redhatsubscriptions")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_redhatsubscriptions")),
    )
    op.create_index(
        "redhatsubscriptions_subscription_id",
        "redhatsubscriptions",
        ["subscription_id"],
        unique=True,
    )


def downgrade(op, tables, tester):
    op.drop_table("redhatsubscriptions")
