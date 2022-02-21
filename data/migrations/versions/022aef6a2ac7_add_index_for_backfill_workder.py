"""add index for backfill workder

Revision ID: 022aef6a2ac7
Revises: 909d725887d3
Create Date: 2022-02-21 13:50:43.204422

"""

# revision identifiers, used by Alembic.
revision = "022aef6a2ac7"
down_revision = "909d725887d3"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_index(
        "manifest_compressed_size_id", "manifest", ["layers_compressed_size", "id"], unique=False
    )


def downgrade(op, tables, tester):
    op.drop_index("manifest_compressed_size_id", table_name="manifest")
