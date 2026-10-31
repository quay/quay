"""add repository digest registration tables and upload hashing columns

Revision ID: a2f338ee672c
Revises: 9fa37f66a9b6
Create Date: 2026-08-18 16:01:07.720229

"""

# revision identifiers, used by Alembic.
revision = "a2f338ee672c"
down_revision = "9fa37f66a9b6"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    # RepositoryBlobDigest
    op.create_table(
        "repositoryblobdigest",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("image_storage_id", sa.Integer(), nullable=False),
        sa.Column("digest", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repositoryblobdigest_repository_id"),
        ),
        sa.ForeignKeyConstraint(
            ["image_storage_id"],
            ["imagestorage.id"],
            name=op.f("fk_repositoryblobdigest_image_storage_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositoryblobdigest")),
    )
    op.create_index(
        "repositoryblobdigest_repository_id_digest",
        "repositoryblobdigest",
        ["repository_id", "digest"],
        unique=True,
    )
    op.create_index(
        "repositoryblobdigest_repository_id_image_storage_id",
        "repositoryblobdigest",
        ["repository_id", "image_storage_id"],
        unique=False,
    )
    op.create_index(
        "repositoryblobdigest_image_storage_id",
        "repositoryblobdigest",
        ["image_storage_id"],
        unique=False,
    )

    # RepositoryManifestDigest
    op.create_table(
        "repositorymanifestdigest",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("manifest_id", sa.Integer(), nullable=False),
        sa.Column("digest", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repositorymanifestdigest_repository_id"),
        ),
        sa.ForeignKeyConstraint(
            ["manifest_id"],
            ["manifest.id"],
            name=op.f("fk_repositorymanifestdigest_manifest_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositorymanifestdigest")),
    )
    op.create_index(
        "repositorymanifestdigest_repository_id_digest",
        "repositorymanifestdigest",
        ["repository_id", "digest"],
        unique=True,
    )
    op.create_index(
        "repositorymanifestdigest_repository_id_manifest_id",
        "repositorymanifestdigest",
        ["repository_id", "manifest_id"],
        unique=False,
    )
    op.create_index(
        "repositorymanifestdigest_manifest_id",
        "repositorymanifestdigest",
        ["manifest_id"],
        unique=False,
    )

    # BlobUpload columns
    op.add_column(
        "blobupload",
        sa.Column("requested_digest_algorithm", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "blobupload",
        sa.Column("requested_digest_state", sa.Text(), nullable=True),
    )

    tester.populate_table(
        "repositoryblobdigest",
        [
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("image_storage_id", tester.TestDataType.Foreign("imagestorage")),
            ("digest", tester.TestDataType.String),
            ("created_at", tester.TestDataType.DateTime),
        ],
    )
    tester.populate_table(
        "repositorymanifestdigest",
        [
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("manifest_id", tester.TestDataType.Foreign("manifest")),
            ("digest", tester.TestDataType.String),
            ("created_at", tester.TestDataType.DateTime),
        ],
    )


def downgrade(op, tables, tester):
    with op.batch_alter_table("blobupload") as batch_op:
        batch_op.drop_column("requested_digest_state")
        batch_op.drop_column("requested_digest_algorithm")

    op.drop_table("repositorymanifestdigest")
    op.drop_table("repositoryblobdigest")
