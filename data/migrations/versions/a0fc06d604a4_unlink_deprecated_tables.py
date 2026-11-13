"""Unlink deprecated tables

Revision ID: a0fc06d604a4
Revises: d94d328733e4
Create Date: 2022-05-27 11:02:09.738779

"""

# revision identifiers, used by Alembic.
revision = "a0fc06d604a4"
down_revision = "46980ea2dde5"

from contextlib import contextmanager

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


class _SkipExistingForeignKeys(object):
    """
    Wraps an Alembic batch operation so that create_foreign_key() is a no-op for constraints that
    already exist.
    """

    def __init__(self, batch_op, existing_names):
        self._batch_op = batch_op
        self._existing_names = existing_names

    def create_foreign_key(self, constraint_name, *args, **kwargs):
        if constraint_name in self._existing_names:
            return
        self._batch_op.create_foreign_key(constraint_name, *args, **kwargs)


@contextmanager
def _batch_add_missing_fks(op, table_name):
    """
    Like op.batch_alter_table(), but create_foreign_key() skips constraints that already exist.

    When downgrading, the later migration that dropped the deprecated tables (8a70b8777089)
    re-creates them with their foreign keys already in place, so adding them again would fail.
    """
    existing = {fk["name"] for fk in sa_inspect(op.get_bind()).get_foreign_keys(table_name)}
    with op.batch_alter_table(table_name) as batch_op:
        yield _SkipExistingForeignKeys(batch_op, existing)


def upgrade(op, tables, tester):
    # DerivedStorageForImage
    with op.batch_alter_table("derivedstorageforimage") as batch_op:
        batch_op.drop_constraint(
            op.f("fk_derivedstorageforimage_derivative_id_imagestorage"),
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f("fk_derivedstorageforimage_source_image_id_image"),
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f("fk_derivedstorageforimage_transformation_constraint"),
            type_="foreignkey",
        )

    # RepositoryTag
    with op.batch_alter_table("repositorytag") as batch_op:
        batch_op.drop_constraint(
            op.f("fk_repositorytag_image_id_image"),
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f("fk_repositorytag_repository_id_repository"),
            type_="foreignkey",
        )

    # TorrentInfo
    with op.batch_alter_table("torrentinfo") as batch_op:
        batch_op.drop_constraint(
            op.f("fk_torrentinfo_storage_id_imagestorage"),
            type_="foreignkey",
        )

    # TagManifest
    with op.batch_alter_table("tagmanifest") as batch_op:
        batch_op.drop_constraint(
            op.f("fk_tagmanifest_tag_id_repositorytag"),
            type_="foreignkey",
        )

    # TagManifestToManifest
    with op.batch_alter_table("tagmanifesttomanifest") as batch_op:
        batch_op.drop_constraint(
            op.f("fk_tagmanifesttomanifest_manifest_id_manifest"),
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f("fk_tagmanifesttomanifest_tag_manifest_id_tagmanifest"),
            type_="foreignkey",
        )

    # TagManifestLabel
    with op.batch_alter_table("tagmanifestlabel") as batch_op:
        batch_op.drop_constraint(
            op.f("fk_tagmanifestlabel_annotated_id_tagmanifest"),
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f("fk_tagmanifestlabel_label_id_label"),
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f("fk_tagmanifestlabel_repository_id_repository"),
            type_="foreignkey",
        )

    # TagManifestLabelMap
    with op.batch_alter_table("tagmanifestlabelmap") as batch_op:
        batch_op.drop_constraint(
            op.f("fk_tagmanifestlabelmap_label_id_label"),
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f("fk_tagmanifestlabelmap_manifest_id_manifest"),
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f("fk_tagmanifestlabelmap_manifest_label_id_manifestlabel"),
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f("fk_tagmanifestlabelmap_tag_manifest_id_tagmanifest"),
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f("fk_tagmanifestlabelmap_tag_manifest_label_id_tagmanifestlabel"),
            type_="foreignkey",
        )

    # TagToRepositoryTag
    with op.batch_alter_table("tagtorepositorytag") as batch_op:
        batch_op.drop_constraint(
            op.f("fk_tagtorepositorytag_repository_id_repository"),
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f("fk_tagtorepositorytag_repository_tag_id_repositorytag"),
            type_="foreignkey",
        )
        batch_op.drop_constraint(op.f("fk_tagtorepositorytag_tag_id_tag"), type_="foreignkey")

    # Image
    with op.batch_alter_table("image") as batch_op:
        batch_op.drop_constraint(op.f("fk_image_repository_id_repository"), type_="foreignkey")
        batch_op.drop_constraint(op.f("fk_image_storage_id_imagestorage"), type_="foreignkey")

    # ManifestLegacyImage
    with op.batch_alter_table("manifestlegacyimage") as batch_op:
        batch_op.drop_constraint(op.f("fk_manifestlegacyimage_image_id_image"), type_="foreignkey")
        batch_op.drop_constraint(
            op.f("fk_manifestlegacyimage_manifest_id_manifest"),
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f("fk_manifestlegacyimage_repository_id_repository"),
            type_="foreignkey",
        )


def downgrade(op, tables, tester):
    # DerivedStorageForImage
    with _batch_add_missing_fks(op, "derivedstorageforimage") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_derivedstorageforimage_derivative_id_imagestorage"),
            "imagestorage",
            ["derivative_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            op.f("fk_derivedstorageforimage_source_image_id_image"),
            "image",
            ["source_image_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            op.f("fk_derivedstorageforimage_transformation_constraint"),
            "imagestoragetransformation",
            ["transformation_id"],
            ["id"],
        )

    # RepositoryTag
    with _batch_add_missing_fks(op, "repositorytag") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_repositorytag_image_id_image"),
            "image",
            ["image_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            op.f("fk_repositorytag_repository_id_repository"),
            "repository",
            ["repository_id"],
            ["id"],
        )

    # TorrentInfo
    with _batch_add_missing_fks(op, "torrentinfo") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_torrentinfo_storage_id_imagestorage"),
            "imagestorage",
            ["storage_id"],
            ["id"],
        )

    # TagManifest
    with _batch_add_missing_fks(op, "tagmanifest") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_tagmanifest_tag_id_repositorytag"),
            "repositorytag",
            ["tag_id"],
            ["id"],
        )

    # TagManifestToManifest
    with _batch_add_missing_fks(op, "tagmanifesttomanifest") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_tagmanifesttomanifest_manifest_id_manifest"),
            "manifest",
            ["manifest_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            op.f("fk_tagmanifesttomanifest_tag_manifest_id_tagmanifest"),
            "tagmanifest",
            ["tag_manifest_id"],
            ["id"],
        )

    # TagManifestLabel
    with _batch_add_missing_fks(op, "tagmanifestlabel") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_tagmanifestlabel_annotated_id_tagmanifest"),
            "tagmanifest",
            ["annotated_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            op.f("fk_tagmanifestlabel_label_id_label"),
            "label",
            ["label_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            op.f("fk_tagmanifestlabel_repository_id_repository"),
            "repository",
            ["repository_id"],
            ["id"],
        )

    # TagManifestLabelMap
    with _batch_add_missing_fks(op, "tagmanifestlabelmap") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_tagmanifestlabelmap_label_id_label"),
            "label",
            ["label_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            op.f("fk_tagmanifestlabelmap_manifest_id_manifest"),
            "manifest",
            ["manifest_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            op.f("fk_tagmanifestlabelmap_manifest_label_id_manifestlabel"),
            "manifest_label",
            ["manifest_label_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            op.f("fk_tagmanifestlabelmap_tag_manifest_id_tagmanifest"),
            "tagmanifest",
            ["tag_manifest_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            op.f("fk_tagmanifestlabelmap_tag_manifest_label_id_tagmanifestlabel"),
            "tagmanifestlabel",
            ["tag_manifest_label_id"],
            ["id"],
        )

    # TagToRepositoryTag
    with _batch_add_missing_fks(op, "tagtorepositorytag") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_tagtorepositorytag_repository_id_repository"),
            "repository",
            ["repository_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            op.f("fk_tagtorepositorytag_repository_tag_id_repositorytag"),
            "repositorytag",
            ["repository_tag_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            op.f("fk_tagtorepositorytag_tag_id_tag"),
            "tag",
            ["tag_id"],
            ["id"],
        )

    # Image
    with _batch_add_missing_fks(op, "image") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_image_repository_id_repository"), "repository", ["repository_id"], ["id"]
        )
        batch_op.create_foreign_key(
            op.f("fk_image_storage_id_imagestorage"), "imagestorage", ["storage_id"], ["id"]
        )

    # ManifestLegacyImage
    with _batch_add_missing_fks(op, "manifestlegacyimage") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_manifestlegacyimage_image_id_image"),
            "image",
            ["image_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            op.f("fk_manifestlegacyimage_manifest_id_manifest"),
            "manifest",
            ["manifest_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            op.f("fk_manifestlegacyimage_repository_id_repository"),
            "repository",
            ["repository_id"],
            ["id"],
        )
