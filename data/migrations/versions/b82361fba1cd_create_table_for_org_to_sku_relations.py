"""Create table for org to sku relations

Revision ID: b82361fba1cd
Revises: 46980ea2dde5
Create Date: 2023-06-07 14:22:09.384808

"""

# revision identifiers, used by Alembic.
revision = "b82361fba1cd"
down_revision = "8a70b8777089"

from typing import Text

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "organizationrhskus",
        sa.Column("id", sa.Integer, nullable=False, autoincrement=True),
        sa.Column("subscription_id", sa.Integer, nullable=False),
        sa.Column("org_id", sa.Integer, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizationrhskus")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name=op.f("fk_organizationrhskus_userid")
        ),
        sa.ForeignKeyConstraint(["org_id"], ["user.id"], name=op.f("fk_organizationrhskus_orgid")),
    )
    op.create_index(
        "organizationrhskus_subscription_id", "organizationrhskus", ["subscription_id"], unique=True
    )
    op.create_index(
        "organizationrhskus_subscription_id_org_id",
        "organizationrhskus",
        ["subscription_id", "org_id"],
        unique=True,
    )
    op.create_index(
        "organizationrhskus_subscription_id_org_id_user_id",
        "organizationrhskus",
        ["subscription_id", "org_id", "user_id"],
        unique=True,
    )


def downgrade(op, tables, tester):
    op.drop_index("organizationrhskus_subscription_id", table_name="organizationrhskus")
    op.drop_index("organizationrhskus_subscription_id_org_id", table_name="organizationrhskus")
    op.drop_index(
        "organizationrhskus_subscription_id_org_id_user_id", table_name="organizationrhskus"
    )
    op.drop_table("organizationrhskus")
