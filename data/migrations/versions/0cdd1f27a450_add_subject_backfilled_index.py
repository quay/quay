"""add subject backfilled index

Revision ID: 0cdd1f27a450
Revises: 946f0e90f9c9
Create Date: 2024-06-21 11:49:00.173665

"""

# revision identifiers, used by Alembic.
revision = "0cdd1f27a450"
down_revision = "946f0e90f9c9"

import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


def upgrade(op, tables, tester):
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    manifest_indexes = inspector.get_indexes("manifest")
    if not "manifest_subject_backfilled" in [i["name"] for i in manifest_indexes]:
        with op.get_context().autocommit_block():
            op.create_index(
                "manifest_subject_backfilled",
                "manifest",
                ["subject_backfilled"],
                unique=False,
                postgresql_concurrently=True,
            )


def downgrade(op, tables, tester):
    op.drop_index("manifest_subject_backfilled", table_name="manifest")
