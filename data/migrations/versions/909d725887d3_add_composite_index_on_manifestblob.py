"""Add composite index on manifestblob

Revision ID: 909d725887d3
Revises: 88e64904d000
Create Date: 2021-04-23 14:48:21.156441

"""

# revision identifiers, used by Alembic.
revision = "909d725887d3"
down_revision = "88e64904d000"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_index(
        "manifestblob_repository_id_blob_id",
        "manifestblob",
        ["repository_id", "blob_id"],
    )


def downgrade(op, tables, tester):
    op.drop_index("manifestblob_repository_id_blob_id", table_name="manifestblob")
