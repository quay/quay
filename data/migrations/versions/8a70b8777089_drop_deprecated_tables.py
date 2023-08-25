"""drop deprecated tables

Revision ID: 8a70b8777089
Revises: a0fc06d604a4
Create Date: 2023-08-01 11:13:34.324472

"""

# revision identifiers, used by Alembic.
revision = "8a70b8777089"
down_revision = "a0fc06d604a4"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.execute("DROP TABLE IF EXISTS repositorysize")
    op.execute("DROP TABLE IF EXISTS image")
    op.execute("DROP TABLE IF EXISTS derivedstorageforimage")
    op.execute("DROP TABLE IF EXISTS repositorytag")
    op.execute("DROP TABLE IF EXISTS torrentinfo")
    op.execute("DROP TABLE IF EXISTS manifestlegacyimage")
    op.execute("DROP TABLE IF EXISTS tagmanifest")
    op.execute("DROP TABLE IF EXISTS tagmanifesttomanifest")
    op.execute("DROP TABLE IF EXISTS tagmanifestlabel")
    op.execute("DROP TABLE IF EXISTS tagmanifestlabelmap")
    op.execute("DROP TABLE IF EXISTS tagtorepositorytag")


def downgrade(op, tables, tester):
    op.create_table(
        "repositorysize",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("repository_id", sa.Integer, nullable=False),
        sa.Column("size_bytes", sa.NUMERIC, nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repositorysize_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositorysizeid")),
    )
    op.create_index(
        "repositorysize_repository_id",
        "repositorysize",
        ["repository_id"],
        unique=True,
    )

    op.create_table(
        "image",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("docker_image_id", sa.String(length=255), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("ancestors", sa.String(length=60535), nullable=True),
        sa.Column("storage_id", sa.Integer(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("comment", UTF8LongText(), nullable=True),
        sa.Column("command", sa.Text(), nullable=True),
        sa.Column("aggregate_size", sa.BigInteger(), nullable=True),
        sa.Column("v1_json_metadata", UTF8LongText(), nullable=True),
        sa.Column("v1_checksum", sa.String(length=255), nullable=True),
        sa.Column(
            "security_indexed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
        sa.Column("security_indexed_engine", sa.Integer(), nullable=False, server_default="-1"),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["repository_id"], ["repository.id"], name=op.f("fk_image_repository_id_repository")
        ),
        sa.ForeignKeyConstraint(
            ["storage_id"], ["imagestorage.id"], name=op.f("fk_image_storage_id_imagestorage")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_image")),
    )
    op.create_index("image_ancestors", "image", ["ancestors"], unique=False, mysql_length=767)
    op.create_index("image_docker_image_id", "image", ["docker_image_id"], unique=False)
    op.create_index("image_parent_id", "image", ["parent_id"], unique=False)
    op.create_index("image_repository_id", "image", ["repository_id"], unique=False)
    op.create_index(
        "image_repository_id_docker_image_id",
        "image",
        ["repository_id", "docker_image_id"],
        unique=True,
    )
    op.create_index("image_security_indexed", "image", ["security_indexed"], unique=False)
    op.create_index(
        "image_security_indexed_engine", "image", ["security_indexed_engine"], unique=False
    )
    op.create_index(
        "image_security_indexed_engine_security_indexed",
        "image",
        ["security_indexed_engine", "security_indexed"],
        unique=False,
    )
    op.create_index("image_storage_id", "image", ["storage_id"], unique=False)

    op.create_table(
        "derivedstorageforimage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_image_id", sa.Integer(), nullable=False),
        sa.Column("derivative_id", sa.Integer(), nullable=False),
        sa.Column("transformation_id", sa.Integer(), nullable=False),
        sa.Column("uniqueness_hash", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["derivative_id"],
            ["imagestorage.id"],
            name=op.f("fk_derivedstorageforimage_derivative_id_imagestorage"),
        ),
        sa.ForeignKeyConstraint(
            ["source_image_id"],
            ["image.id"],
            name=op.f("fk_derivedstorageforimage_source_image_id_image"),
        ),
        sa.ForeignKeyConstraint(
            ["transformation_id"],
            ["imagestoragetransformation.id"],
            name=op.f("fk_derivedstorageforimage_transformation_constraint"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_derivedstorageforimage")),
    )
    op.create_index(
        "derivedstorageforimage_derivative_id",
        "derivedstorageforimage",
        ["derivative_id"],
        unique=False,
    )
    op.create_index(
        "derivedstorageforimage_source_image_id",
        "derivedstorageforimage",
        ["source_image_id"],
        unique=False,
    )
    op.create_index(
        "uniqueness_index",
        "derivedstorageforimage",
        ["source_image_id", "transformation_id", "uniqueness_hash"],
        unique=True,
    )
    op.create_index(
        "derivedstorageforimage_transformation_id",
        "derivedstorageforimage",
        ["transformation_id"],
        unique=False,
    )

    op.create_table(
        "repositorytag",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("image_id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("lifetime_start_ts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lifetime_end_ts", sa.Integer(), nullable=True),
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()),
        sa.Column(
            "reversion", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()
        ),
        sa.ForeignKeyConstraint(
            ["image_id"], ["image.id"], name=op.f("fk_repositorytag_image_id_image")
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repositorytag_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositorytag")),
    )
    op.create_index("repositorytag_image_id", "repositorytag", ["image_id"], unique=False)
    op.create_index(
        "repositorytag_lifetime_end_ts", "repositorytag", ["lifetime_end_ts"], unique=False
    )
    op.create_index("repositorytag_repository_id", "repositorytag", ["repository_id"], unique=False)
    op.create_index(
        "repositorytag_repository_id_name", "repositorytag", ["repository_id", "name"], unique=False
    )
    op.create_index(
        "repositorytag_repository_id_name_lifetime_end_ts",
        "repositorytag",
        ["repository_id", "name", "lifetime_end_ts"],
        unique=True,
    )

    op.create_table(
        "torrentinfo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("storage_id", sa.Integer(), nullable=False),
        sa.Column("piece_length", sa.Integer(), nullable=False),
        sa.Column("pieces", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["storage_id"], ["imagestorage.id"], name=op.f("fk_torrentinfo_storage_id_imagestorage")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_torrentinfo")),
    )
    op.create_index("torrentinfo_storage_id", "torrentinfo", ["storage_id"], unique=False)
    op.create_index(
        "torrentinfo_storage_id_piece_length",
        "torrentinfo",
        ["storage_id", "piece_length"],
        unique=True,
    )

    op.create_table(
        "manifestlegacyimage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("manifest_id", sa.Integer(), nullable=False),
        sa.Column("image_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["image_id"], ["image.id"], name=op.f("fk_manifestlegacyimage_image_id_image")
        ),
        sa.ForeignKeyConstraint(
            ["manifest_id"],
            ["manifest.id"],
            name=op.f("fk_manifestlegacyimage_manifest_id_manifest"),
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_manifestlegacyimage_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manifestlegacyimage")),
    )
    op.create_index(
        "manifestlegacyimage_image_id", "manifestlegacyimage", ["image_id"], unique=False
    )
    op.create_index(
        "manifestlegacyimage_manifest_id", "manifestlegacyimage", ["manifest_id"], unique=True
    )
    op.create_index(
        "manifestlegacyimage_repository_id", "manifestlegacyimage", ["repository_id"], unique=False
    )

    op.create_table(
        "tagmanifest",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("digest", sa.String(length=255), nullable=False),
        sa.Column("json_data", UTF8LongText(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["repositorytag.id"], name=op.f("fk_tagmanifest_tag_id_repositorytag")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tagmanifest")),
    )
    op.create_index("tagmanifest_digest", "tagmanifest", ["digest"], unique=False)
    op.create_index("tagmanifest_tag_id", "tagmanifest", ["tag_id"], unique=True)

    op.create_table(
        "tagmanifesttomanifest",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tag_manifest_id", sa.Integer(), nullable=False),
        sa.Column("manifest_id", sa.Integer(), nullable=False),
        sa.Column("broken", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()),
        sa.ForeignKeyConstraint(
            ["manifest_id"],
            ["manifest.id"],
            name=op.f("fk_tagmanifesttomanifest_manifest_id_manifest"),
        ),
        sa.ForeignKeyConstraint(
            ["tag_manifest_id"],
            ["tagmanifest.id"],
            name=op.f("fk_tagmanifesttomanifest_tag_manifest_id_tagmanifest"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tagmanifesttomanifest")),
    )
    op.create_index(
        "tagmanifesttomanifest_broken", "tagmanifesttomanifest", ["broken"], unique=False
    )

    op.create_table(
        "tagmanifestlabel",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("annotated_id", sa.Integer(), nullable=False),
        sa.Column("label_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["annotated_id"],
            ["tagmanifest.id"],
            name=op.f("fk_tagmanifestlabel_annotated_id_tagmanifest"),
        ),
        sa.ForeignKeyConstraint(
            ["label_id"], ["label.id"], name=op.f("fk_tagmanifestlabel_label_id_label")
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_tagmanifestlabel_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tagmanifestlabel")),
    )
    op.create_index(
        "tagmanifestlabel_annotated_id", "tagmanifestlabel", ["annotated_id"], unique=False
    )
    op.create_index(
        "tagmanifestlabel_annotated_id_label_id",
        "tagmanifestlabel",
        ["annotated_id", "label_id"],
        unique=True,
    )
    op.create_index("tagmanifestlabel_label_id", "tagmanifestlabel", ["label_id"], unique=False)
    op.create_index(
        "tagmanifestlabel_repository_id", "tagmanifestlabel", ["repository_id"], unique=False
    )

    op.create_table(
        "tagmanifestlabelmap",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tag_manifest_id", sa.Integer(), nullable=False),
        sa.Column("manifest_id", sa.Integer(), nullable=True),
        sa.Column("label_id", sa.Integer(), nullable=False),
        sa.Column("tag_manifest_label_id", sa.Integer(), nullable=False),
        sa.Column("manifest_label_id", sa.Integer(), nullable=True),
        sa.Column(
            "broken_manifest",
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
        sa.ForeignKeyConstraint(
            ["label_id"], ["label.id"], name=op.f("fk_tagmanifestlabelmap_label_id_label")
        ),
        sa.ForeignKeyConstraint(
            ["manifest_id"],
            ["manifest.id"],
            name=op.f("fk_tagmanifestlabelmap_manifest_id_manifest"),
        ),
        sa.ForeignKeyConstraint(
            ["manifest_label_id"],
            ["manifestlabel.id"],
            name=op.f("fk_tagmanifestlabelmap_manifest_label_id_manifestlabel"),
        ),
        sa.ForeignKeyConstraint(
            ["tag_manifest_id"],
            ["tagmanifest.id"],
            name=op.f("fk_tagmanifestlabelmap_tag_manifest_id_tagmanifest"),
        ),
        sa.ForeignKeyConstraint(
            ["tag_manifest_label_id"],
            ["tagmanifestlabel.id"],
            name=op.f("fk_tagmanifestlabelmap_tag_manifest_label_id_tagmanifestlabel"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tagmanifestlabelmap")),
    )
    op.create_index(
        "tagmanifestlabelmap_broken_manifest",
        "tagmanifestlabelmap",
        ["broken_manifest"],
        unique=False,
    )
    op.create_index(
        "tagmanifestlabelmap_label_id", "tagmanifestlabelmap", ["label_id"], unique=False
    )
    op.create_index(
        "tagmanifestlabelmap_manifest_id", "tagmanifestlabelmap", ["manifest_id"], unique=False
    )
    op.create_index(
        "tagmanifestlabelmap_manifest_label_id",
        "tagmanifestlabelmap",
        ["manifest_label_id"],
        unique=False,
    )
    op.create_index(
        "tagmanifestlabelmap_tag_manifest_id",
        "tagmanifestlabelmap",
        ["tag_manifest_id"],
        unique=False,
    )
    op.create_index(
        "tagmanifestlabelmap_tag_manifest_label_id",
        "tagmanifestlabelmap",
        ["tag_manifest_label_id"],
        unique=False,
    )

    op.create_table(
        "tagtorepositorytag",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("repository_tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_tagtorepositorytag_repository_id_repository"),
        ),
        sa.ForeignKeyConstraint(
            ["repository_tag_id"],
            ["repositorytag.id"],
            name=op.f("fk_tagtorepositorytag_repository_tag_id_repositorytag"),
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["tag.id"], name=op.f("fk_tagtorepositorytag_tag_id_tag")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tagtorepositorytag")),
    )
    op.create_index(
        "tagtorepositorytag_repository_id", "tagtorepositorytag", ["repository_id"], unique=False
    )
    op.create_index(
        "tagtorepositorytag_repository_tag_id",
        "tagtorepositorytag",
        ["repository_tag_id"],
        unique=True,
    )
    op.create_index("tagtorepositorytag_tag_id", "tagtorepositorytag", ["tag_id"], unique=True)
