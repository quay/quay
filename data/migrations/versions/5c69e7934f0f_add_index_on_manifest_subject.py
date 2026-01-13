"""Add index on manifest_subject

Revision ID: 5c69e7934f0f
Revises: 9307c3d604b4
Create Date: 2026-01-13 10:01:12.710515

"""

# revision identifiers, used by Alembic.
revision = "5c69e7934f0f"
down_revision = "9307c3d604b4"

import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


def upgrade(op, tables, tester):
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    manifest_indexes = inspector.get_indexes("manifest")
    if "manifest_subject" not in [i["name"] for i in manifest_indexes]:
        with op.get_context().autocommit_block():
            op.create_index(
                "manifest_subject",
                "manifest",
                ["subject"],
                unique=False,
                postgresql_concurrently=True,
            )


def downgrade(op, tables, tester):
    op.drop_index("manifest_subject", table_name="manifest")
