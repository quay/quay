"""drop unique constraint on org sku table

Revision ID: 3634f2df3c5b
Revises: 8e97c2cfee57
Create Date: 2024-11-04 14:14:21.736496

"""

# revision identifiers, used by Alembic.
revision = "3634f2df3c5b"
down_revision = "8e97c2cfee57"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    # Drop the existing unique index
    op.drop_index("organizationrhskus_subscription_id", table_name="organizationrhskus")
    op.create_index(
        "organizationrhskus_subscription_id",
        "organizationrhskus",
        ["subscription_id"],
        unique=False,
    )


def downgrade(op, tables, tester):
    # Re-add the unique index if we need to rollback
    op.drop_index("organizationrhskus_subscription_id", table_name="organizationrhskus")
    op.create_index(
        "organizationrhskus_subscription_id", "organizationrhskus", ["subscription_id"], unique=True
    )
