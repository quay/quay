"""
Add OCI/App models.

Revision ID: 7a525c68eb13
Revises: e2894a3a3c19
Create Date: 2017-01-24 16:25:52.170277
"""

# revision identifiers, used by Alembic.
revision = "7a525c68eb13"
down_revision = "e2894a3a3c19"

import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.sql import table, column
from util.migrate import UTF8LongText, UTF8CharField


def upgrade(op, tables, tester):
    op.create_table(
        "tagkind",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tagkind")),
    )
    op.create_index("tagkind_name", "tagkind", ["name"], unique=True)

    op.create_table(
        "blobplacementlocation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blobplacementlocation")),
    )
    op.create_index("blobplacementlocation_name", "blobplacementlocation", ["name"], unique=True)

    op.create_table(
        "blob",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("digest", sa.String(length=255), nullable=False),
        sa.Column("media_type_id", sa.Integer(), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("uncompressed_size", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["media_type_id"], ["mediatype.id"], name=op.f("fk_blob_media_type_id_mediatype")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blob")),
    )
    op.create_index("blob_digest", "blob", ["digest"], unique=True)
    op.create_index("blob_media_type_id", "blob", ["media_type_id"], unique=False)

    op.create_table(
        "blobplacementlocationpreference",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["blobplacementlocation.id"],
            name=op.f("fk_blobplacementlocpref_locid_blobplacementlocation"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name=op.f("fk_blobplacementlocationpreference_user_id_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blobplacementlocationpreference")),
    )
    op.create_index(
        "blobplacementlocationpreference_location_id",
        "blobplacementlocationpreference",
        ["location_id"],
        unique=False,
    )
    op.create_index(
        "blobplacementlocationpreference_user_id",
        "blobplacementlocationpreference",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "manifest",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("digest", sa.String(length=255), nullable=False),
        sa.Column("media_type_id", sa.Integer(), nullable=False),
        sa.Column("manifest_json", UTF8LongText, nullable=False),
        sa.ForeignKeyConstraint(
            ["media_type_id"], ["mediatype.id"], name=op.f("fk_manifest_media_type_id_mediatype")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manifest")),
    )
    op.create_index("manifest_digest", "manifest", ["digest"], unique=True)
    op.create_index("manifest_media_type_id", "manifest", ["media_type_id"], unique=False)

    op.create_table(
        "manifestlist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("digest", sa.String(length=255), nullable=False),
        sa.Column("manifest_list_json", UTF8LongText, nullable=False),
        sa.Column("schema_version", UTF8CharField(length=255), nullable=False),
        sa.Column("media_type_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["media_type_id"],
            ["mediatype.id"],
            name=op.f("fk_manifestlist_media_type_id_mediatype"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manifestlist")),
    )
    op.create_index("manifestlist_digest", "manifestlist", ["digest"], unique=True)
    op.create_index("manifestlist_media_type_id", "manifestlist", ["media_type_id"], unique=False)

    op.create_table(
        "bittorrentpieces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("blob_id", sa.Integer(), nullable=False),
        sa.Column("pieces", UTF8LongText, nullable=False),
        sa.Column("piece_length", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["blob_id"], ["blob.id"], name=op.f("fk_bittorrentpieces_blob_id_blob")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bittorrentpieces")),
    )
    op.create_index("bittorrentpieces_blob_id", "bittorrentpieces", ["blob_id"], unique=False)
    op.create_index(
        "bittorrentpieces_blob_id_piece_length",
        "bittorrentpieces",
        ["blob_id", "piece_length"],
        unique=True,
    )

    op.create_table(
        "blobplacement",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("blob_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["blob_id"], ["blob.id"], name=op.f("fk_blobplacement_blob_id_blob")
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["blobplacementlocation.id"],
            name=op.f("fk_blobplacement_location_id_blobplacementlocation"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blobplacement")),
    )
    op.create_index("blobplacement_blob_id", "blobplacement", ["blob_id"], unique=False)
    op.create_index(
        "blobplacement_blob_id_location_id",
        "blobplacement",
        ["blob_id", "location_id"],
        unique=True,
    )
    op.create_index("blobplacement_location_id", "blobplacement", ["location_id"], unique=False)

    op.create_table(
        "blobuploading",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=255), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("byte_count", sa.BigInteger(), nullable=False),
        sa.Column("uncompressed_byte_count", sa.BigInteger(), nullable=True),
        sa.Column("chunk_count", sa.BigInteger(), nullable=False),
        sa.Column("storage_metadata", UTF8LongText, nullable=True),
        sa.Column("sha_state", UTF8LongText, nullable=True),
        sa.Column("piece_sha_state", UTF8LongText, nullable=True),
        sa.Column("piece_hashes", UTF8LongText, nullable=True),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["blobplacementlocation.id"],
            name=op.f("fk_blobuploading_location_id_blobplacementlocation"),
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_blobuploading_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blobuploading")),
    )
    op.create_index("blobuploading_created", "blobuploading", ["created"], unique=False)
    op.create_index("blobuploading_location_id", "blobuploading", ["location_id"], unique=False)
    op.create_index("blobuploading_repository_id", "blobuploading", ["repository_id"], unique=False)
    op.create_index(
        "blobuploading_repository_id_uuid", "blobuploading", ["repository_id", "uuid"], unique=True
    )
    op.create_index("blobuploading_uuid", "blobuploading", ["uuid"], unique=True)

    op.create_table(
        "derivedimage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=255), nullable=False),
        sa.Column("source_manifest_id", sa.Integer(), nullable=False),
        sa.Column("derived_manifest_json", UTF8LongText, nullable=False),
        sa.Column("media_type_id", sa.Integer(), nullable=False),
        sa.Column("blob_id", sa.Integer(), nullable=False),
        sa.Column("uniqueness_hash", sa.String(length=255), nullable=False),
        sa.Column("signature_blob_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["blob_id"], ["blob.id"], name=op.f("fk_derivedimage_blob_id_blob")
        ),
        sa.ForeignKeyConstraint(
            ["media_type_id"],
            ["mediatype.id"],
            name=op.f("fk_derivedimage_media_type_id_mediatype"),
        ),
        sa.ForeignKeyConstraint(
            ["signature_blob_id"], ["blob.id"], name=op.f("fk_derivedimage_signature_blob_id_blob")
        ),
        sa.ForeignKeyConstraint(
            ["source_manifest_id"],
            ["manifest.id"],
            name=op.f("fk_derivedimage_source_manifest_id_manifest"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_derivedimage")),
    )
    op.create_index("derivedimage_blob_id", "derivedimage", ["blob_id"], unique=False)
    op.create_index("derivedimage_media_type_id", "derivedimage", ["media_type_id"], unique=False)
    op.create_index(
        "derivedimage_signature_blob_id", "derivedimage", ["signature_blob_id"], unique=False
    )
    op.create_index(
        "derivedimage_source_manifest_id", "derivedimage", ["source_manifest_id"], unique=False
    )
    op.create_index(
        "derivedimage_source_manifest_id_blob_id",
        "derivedimage",
        ["source_manifest_id", "blob_id"],
        unique=True,
    )
    op.create_index(
        "derivedimage_source_manifest_id_media_type_id_uniqueness_hash",
        "derivedimage",
        ["source_manifest_id", "media_type_id", "uniqueness_hash"],
        unique=True,
    )
    op.create_index(
        "derivedimage_uniqueness_hash", "derivedimage", ["uniqueness_hash"], unique=True
    )
    op.create_index("derivedimage_uuid", "derivedimage", ["uuid"], unique=True)

    op.create_table(
        "manifestblob",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("manifest_id", sa.Integer(), nullable=False),
        sa.Column("blob_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["blob_id"], ["blob.id"], name=op.f("fk_manifestblob_blob_id_blob")
        ),
        sa.ForeignKeyConstraint(
            ["manifest_id"], ["manifest.id"], name=op.f("fk_manifestblob_manifest_id_manifest")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manifestblob")),
    )
    op.create_index("manifestblob_blob_id", "manifestblob", ["blob_id"], unique=False)
    op.create_index("manifestblob_manifest_id", "manifestblob", ["manifest_id"], unique=False)
    op.create_index(
        "manifestblob_manifest_id_blob_id", "manifestblob", ["manifest_id", "blob_id"], unique=True
    )

    op.create_table(
        "manifestlabel",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("annotated_id", sa.Integer(), nullable=False),
        sa.Column("label_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["annotated_id"], ["manifest.id"], name=op.f("fk_manifestlabel_annotated_id_manifest")
        ),
        sa.ForeignKeyConstraint(
            ["label_id"], ["label.id"], name=op.f("fk_manifestlabel_label_id_label")
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_manifestlabel_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manifestlabel")),
    )
    op.create_index("manifestlabel_annotated_id", "manifestlabel", ["annotated_id"], unique=False)
    op.create_index("manifestlabel_label_id", "manifestlabel", ["label_id"], unique=False)
    op.create_index("manifestlabel_repository_id", "manifestlabel", ["repository_id"], unique=False)
    op.create_index(
        "manifestlabel_repository_id_annotated_id_label_id",
        "manifestlabel",
        ["repository_id", "annotated_id", "label_id"],
        unique=True,
    )

    op.create_table(
        "manifestlayer",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("blob_id", sa.Integer(), nullable=False),
        sa.Column("manifest_id", sa.Integer(), nullable=False),
        sa.Column("manifest_index", sa.BigInteger(), nullable=False),
        sa.Column("metadata_json", UTF8LongText, nullable=False),
        sa.ForeignKeyConstraint(
            ["blob_id"], ["blob.id"], name=op.f("fk_manifestlayer_blob_id_blob")
        ),
        sa.ForeignKeyConstraint(
            ["manifest_id"], ["manifest.id"], name=op.f("fk_manifestlayer_manifest_id_manifest")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manifestlayer")),
    )
    op.create_index("manifestlayer_blob_id", "manifestlayer", ["blob_id"], unique=False)
    op.create_index("manifestlayer_manifest_id", "manifestlayer", ["manifest_id"], unique=False)
    op.create_index(
        "manifestlayer_manifest_id_manifest_index",
        "manifestlayer",
        ["manifest_id", "manifest_index"],
        unique=True,
    )
    op.create_index(
        "manifestlayer_manifest_index", "manifestlayer", ["manifest_index"], unique=False
    )

    op.create_table(
        "manifestlistmanifest",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("manifest_list_id", sa.Integer(), nullable=False),
        sa.Column("manifest_id", sa.Integer(), nullable=False),
        sa.Column("operating_system", UTF8CharField(length=255), nullable=True),
        sa.Column("architecture", UTF8CharField(length=255), nullable=True),
        sa.Column("platform_json", UTF8LongText, nullable=True),
        sa.Column("media_type_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["manifest_id"],
            ["manifest.id"],
            name=op.f("fk_manifestlistmanifest_manifest_id_manifest"),
        ),
        sa.ForeignKeyConstraint(
            ["manifest_list_id"],
            ["manifestlist.id"],
            name=op.f("fk_manifestlistmanifest_manifest_list_id_manifestlist"),
        ),
        sa.ForeignKeyConstraint(
            ["media_type_id"],
            ["mediatype.id"],
            name=op.f("fk_manifestlistmanifest_media_type_id_mediatype"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manifestlistmanifest")),
    )
    op.create_index(
        "manifestlistmanifest_manifest_id", "manifestlistmanifest", ["manifest_id"], unique=False
    )
    op.create_index(
        "manifestlistmanifest_manifest_list_id",
        "manifestlistmanifest",
        ["manifest_list_id"],
        unique=False,
    )
    op.create_index(
        "manifestlistmanifest_manifest_listid_os_arch_mtid",
        "manifestlistmanifest",
        ["manifest_list_id", "operating_system", "architecture", "media_type_id"],
        unique=False,
    )
    op.create_index(
        "manifestlistmanifest_manifest_listid_mtid",
        "manifestlistmanifest",
        ["manifest_list_id", "media_type_id"],
        unique=False,
    )
    op.create_index(
        "manifestlistmanifest_media_type_id",
        "manifestlistmanifest",
        ["media_type_id"],
        unique=False,
    )

    op.create_table(
        "tag",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", UTF8CharField(length=190), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("manifest_list_id", sa.Integer(), nullable=True),
        sa.Column("lifetime_start", sa.BigInteger(), nullable=False),
        sa.Column("lifetime_end", sa.BigInteger(), nullable=True),
        sa.Column("hidden", sa.Boolean(), nullable=False),
        sa.Column("reverted", sa.Boolean(), nullable=False),
        sa.Column("protected", sa.Boolean(), nullable=False),
        sa.Column("tag_kind_id", sa.Integer(), nullable=False),
        sa.Column("linked_tag_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["linked_tag_id"], ["tag.id"], name=op.f("fk_tag_linked_tag_id_tag")
        ),
        sa.ForeignKeyConstraint(
            ["manifest_list_id"],
            ["manifestlist.id"],
            name=op.f("fk_tag_manifest_list_id_manifestlist"),
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"], ["repository.id"], name=op.f("fk_tag_repository_id_repository")
        ),
        sa.ForeignKeyConstraint(
            ["tag_kind_id"], ["tagkind.id"], name=op.f("fk_tag_tag_kind_id_tagkind")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tag")),
    )
    op.create_index("tag_lifetime_end", "tag", ["lifetime_end"], unique=False)
    op.create_index("tag_linked_tag_id", "tag", ["linked_tag_id"], unique=False)
    op.create_index("tag_manifest_list_id", "tag", ["manifest_list_id"], unique=False)
    op.create_index("tag_repository_id", "tag", ["repository_id"], unique=False)
    op.create_index(
        "tag_repository_id_name_hidden", "tag", ["repository_id", "name", "hidden"], unique=False
    )
    op.create_index(
        "tag_repository_id_name_lifetime_end",
        "tag",
        ["repository_id", "name", "lifetime_end"],
        unique=True,
    )
    op.create_index("tag_repository_id_name", "tag", ["repository_id", "name"], unique=False)
    op.create_index("tag_tag_kind_id", "tag", ["tag_kind_id"], unique=False)

    op.create_table(
        "manifestlayerdockerv1",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("manifest_layer_id", sa.Integer(), nullable=False),
        sa.Column("image_id", UTF8CharField(length=255), nullable=False),
        sa.Column("checksum", UTF8CharField(length=255), nullable=False),
        sa.Column("compat_json", UTF8LongText, nullable=False),
        sa.ForeignKeyConstraint(
            ["manifest_layer_id"],
            ["manifestlayer.id"],
            name=op.f("fk_manifestlayerdockerv1_manifest_layer_id_manifestlayer"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manifestlayerdockerv1")),
    )
    op.create_index(
        "manifestlayerdockerv1_image_id", "manifestlayerdockerv1", ["image_id"], unique=False
    )
    op.create_index(
        "manifestlayerdockerv1_manifest_layer_id",
        "manifestlayerdockerv1",
        ["manifest_layer_id"],
        unique=False,
    )

    op.create_table(
        "manifestlayerscan",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("layer_id", sa.Integer(), nullable=False),
        sa.Column("scannable", sa.Boolean(), nullable=False),
        sa.Column("scanned_by", UTF8CharField(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["layer_id"],
            ["manifestlayer.id"],
            name=op.f("fk_manifestlayerscan_layer_id_manifestlayer"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manifestlayerscan")),
    )
    op.create_index("manifestlayerscan_layer_id", "manifestlayerscan", ["layer_id"], unique=True)

    blobplacementlocation_table = table(
        "blobplacementlocation", column("id", sa.Integer()), column("name", sa.String()),
    )

    op.bulk_insert(
        blobplacementlocation_table, [{"name": "local_eu"}, {"name": "local_us"},],
    )

    op.bulk_insert(
        tables.mediatype,
        [
            {"name": "application/vnd.cnr.blob.v0.tar+gzip"},
            {"name": "application/vnd.cnr.package-manifest.helm.v0.json"},
            {"name": "application/vnd.cnr.package-manifest.kpm.v0.json"},
            {"name": "application/vnd.cnr.package-manifest.docker-compose.v0.json"},
            {"name": "application/vnd.cnr.package.kpm.v0.tar+gzip"},
            {"name": "application/vnd.cnr.package.helm.v0.tar+gzip"},
            {"name": "application/vnd.cnr.package.docker-compose.v0.tar+gzip"},
            {"name": "application/vnd.cnr.manifests.v0.json"},
            {"name": "application/vnd.cnr.manifest.list.v0.json"},
        ],
    )

    tagkind_table = table("tagkind", column("id", sa.Integer()), column("name", sa.String()),)

    op.bulk_insert(
        tagkind_table,
        [{"id": 1, "name": "tag"}, {"id": 2, "name": "release"}, {"id": 3, "name": "channel"},],
    )


def downgrade(op, tables, tester):
    op.drop_table("manifestlayerscan")
    op.drop_table("manifestlayerdockerv1")
    op.drop_table("tag")
    op.drop_table("manifestlistmanifest")
    op.drop_table("manifestlayer")
    op.drop_table("manifestlabel")
    op.drop_table("manifestblob")
    op.drop_table("derivedimage")
    op.drop_table("blobuploading")
    op.drop_table("blobplacement")
    op.drop_table("bittorrentpieces")
    op.drop_table("manifestlist")
    op.drop_table("manifest")
    op.drop_table("blobplacementlocationpreference")
    op.drop_table("blob")
    op.drop_table("tagkind")
    op.drop_table("blobplacementlocation")
