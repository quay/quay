"""Create manifestsubject table

Revision ID: 946f0e90f9c9
Revises: 2062bbd5ef0e
Create Date: 2023-11-17 12:06:16.662150

"""

# revision identifiers, used by Alembic.
revision = "946f0e90f9c9"
down_revision = "36cd2b747a08"

import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


def upgrade(op, tables, tester):
    bind = op.get_bind()

    inspector = Inspector.from_engine(bind)
    manifest_columns = inspector.get_columns("manifest")
    manifest_indexes = inspector.get_indexes("manifest")

    if not "subject" in [c["name"] for c in manifest_columns]:
        op.add_column("manifest", sa.Column("subject", sa.String(length=255), nullable=True))

    if not "subject_backfilled" in [c["name"] for c in manifest_columns]:
        op.add_column("manifest", sa.Column("subject_backfilled", sa.Boolean()))

    if not "manifest_repository_id_subject" in [i["name"] for i in manifest_indexes]:
        op.create_index(
            "manifest_repository_id_subject",
            "manifest",
            ["repository_id", "subject"],
            unique=False,
        )


def downgrade(op, tables, tester):
    op.drop_index("manifest_repository_id_subject", table_name="manifest")
    op.drop_column("manifest", "subject")
    op.drop_column("manifest", "subject_backfilled")
