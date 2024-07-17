"""Add artifact_type column

Revision ID: 3f8d7acdf7f9
Revises: 8a7ba94c2e84
Create Date: 2024-07-16 13:34:38.682629

"""

# revision identifiers, used by Alembic.
revision = "3f8d7acdf7f9"
down_revision = "8a7ba94c2e84"

import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


def upgrade(op, tables, tester):
    bind = op.get_bind()

    inspector = Inspector.from_engine(bind)
    manifest_columns = inspector.get_columns("manifest")
    manifest_indexes = inspector.get_indexes("manifest")

    if not "artifact_type" in [c["name"] for c in manifest_columns]:
        op.add_column("manifest", sa.Column("artifact_type", sa.String(length=255), nullable=True))

    if not "artifact_type_backfilled" in [c["name"] for c in manifest_columns]:
        op.add_column("manifest", sa.Column("artifact_type_backfilled", sa.Boolean()))

    if not "manifest_repository_id_artifact_type" in [i["name"] for i in manifest_indexes]:
        with op.get_context().autocommit_block():
            op.create_index(
                "manifest_repository_id_artifact_type",
                "manifest",
                ["repository_id", "artifact_type"],
                unique=False,
                postgresql_concurrently=True,
            )

    if not "manifest_artifact_type_backfilled" in [i["name"] for i in manifest_indexes]:
        with op.get_context().autocommit_block():
            op.create_index(
                "manifest_artifact_type_backfilled",
                "manifest",
                ["artifact_type_backfilled"],
                unique=False,
                postgresql_concurrently=True,
            )


def downgrade(op, tables, tester):
    op.drop_index("manifest_repository_id_artifact_type", table_name="manifest")
    op.drop_index("manifest_artifact_type_backfilled", table_name="manifest")
    op.drop_column("manifest", "artifact_type")
    op.drop_column("manifest", "artifact_type_backfilled")
