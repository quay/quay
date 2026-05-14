"""add multi-algorithm digest support

Revision ID: f6e3ad07cffd
Revises: c3d4e5f6a7b8
Create Date: 2026-05-13 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "f6e3ad07cffd"
down_revision = "c3d4e5f6a7b8"

import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


def upgrade(op, tables, tester):
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    table_names = inspector.get_table_names()

    # Create the digestalias table if it does not already exist.
    if "digestalias" not in table_names:
        op.create_table(
            "digestalias",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("digest", sa.String(length=512), nullable=False),
            sa.Column("image_storage_id", sa.Integer(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(
                ["image_storage_id"],
                ["imagestorage.id"],
                name=op.f("fk_digestalias_image_storage_id_imagestorage"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_digestalias")),
        )
        op.create_index(
            "digestalias_digest",
            "digestalias",
            ["digest"],
            unique=True,
        )
        op.create_index(
            "digestalias_image_storage_id",
            "digestalias",
            ["image_storage_id"],
            unique=False,
        )

    # Add new columns to blobupload for tracking non-SHA-256 hash state.
    blobupload_columns = [c["name"] for c in inspector.get_columns("blobupload")]

    with op.batch_alter_table("blobupload") as batch_op:
        if "client_hash_state" not in blobupload_columns:
            batch_op.add_column(sa.Column("client_hash_state", sa.Text(), nullable=True))
        if "client_hash_algorithm" not in blobupload_columns:
            batch_op.add_column(
                sa.Column("client_hash_algorithm", sa.String(length=32), nullable=True)
            )

    # ### population of test data ### #
    tester.populate_table(
        "digestalias",
        [
            ("digest", tester.TestDataType.String),
            ("image_storage_id", tester.TestDataType.Foreign("imagestorage")),
            ("created_at", tester.TestDataType.DateTime),
        ],
    )
    tester.populate_column("blobupload", "client_hash_state", tester.TestDataType.String)
    tester.populate_column("blobupload", "client_hash_algorithm", tester.TestDataType.String)
    # ### end population of test data ### #


def downgrade(op, tables, tester):
    # Remove new columns from blobupload first (reverse order of upgrade).
    with op.batch_alter_table("blobupload") as batch_op:
        batch_op.drop_column("client_hash_algorithm")
        batch_op.drop_column("client_hash_state")

    # Drop the digestalias table.
    op.drop_table("digestalias")
