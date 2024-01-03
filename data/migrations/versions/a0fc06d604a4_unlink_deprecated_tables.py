"""Unlink deprecated tables

Revision ID: a0fc06d604a4
Revises: d94d328733e4
Create Date: 2022-05-27 11:02:09.738779

"""

# revision identifiers, used by Alembic.
revision = "a0fc06d604a4"
down_revision = "46980ea2dde5"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    # DerivedStorageForImage
    op.drop_constraint(
        op.f("fk_derivedstorageforimage_derivative_id_imagestorage"),
        "derivedstorageforimage",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_derivedstorageforimage_source_image_id_image"),
        "derivedstorageforimage",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_derivedstorageforimage_transformation_constraint"),
        "derivedstorageforimage",
        type_="foreignkey",
    )

    # RepositoryTag
    op.drop_constraint(
        op.f("fk_repositorytag_image_id_image"),
        "repositorytag",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_repositorytag_repository_id_repository"),
        "repositorytag",
        type_="foreignkey",
    )

    # TorrentInfo
    op.drop_constraint(
        op.f("fk_torrentinfo_storage_id_imagestorage"),
        "torrentinfo",
        type_="foreignkey",
    )

    # TagManifest
    op.drop_constraint(
        op.f("fk_tagmanifest_tag_id_repositorytag"),
        "tagmanifest",
        type_="foreignkey",
    )

    # TagManifestToManifest
    op.drop_constraint(
        op.f("fk_tagmanifesttomanifest_manifest_id_manifest"),
        "tagmanifesttomanifest",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_tagmanifesttomanifest_tag_manifest_id_tagmanifest"),
        "tagmanifesttomanifest",
        type_="foreignkey",
    )

    # TagManifestLabel
    op.drop_constraint(
        op.f("fk_tagmanifestlabel_annotated_id_tagmanifest"),
        "tagmanifestlabel",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_tagmanifestlabel_label_id_label"),
        "tagmanifestlabel",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_tagmanifestlabel_repository_id_repository"),
        "tagmanifestlabel",
        type_="foreignkey",
    )

    # TagManifestLabelMap
    op.drop_constraint(
        op.f("fk_tagmanifestlabelmap_label_id_label"),
        "tagmanifestlabelmap",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_tagmanifestlabelmap_manifest_id_manifest"),
        "tagmanifestlabelmap",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_tagmanifestlabelmap_manifest_label_id_manifestlabel"),
        "tagmanifestlabelmap",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_tagmanifestlabelmap_tag_manifest_id_tagmanifest"),
        "tagmanifestlabelmap",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_tagmanifestlabelmap_tag_manifest_label_id_tagmanifestlabel"),
        "tagmanifestlabelmap",
        type_="foreignkey",
    )

    # TagToRepositoryTag
    op.drop_constraint(
        op.f("fk_tagtorepositorytag_repository_id_repository"),
        "tagtorepositorytag",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_tagtorepositorytag_repository_tag_id_repositorytag"),
        "tagtorepositorytag",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_tagtorepositorytag_tag_id_tag"), "tagtorepositorytag", type_="foreignkey"
    )

    # Image
    op.drop_constraint(op.f("fk_image_repository_id_repository"), "image", type_="foreignkey")
    op.drop_constraint(op.f("fk_image_storage_id_imagestorage"), "image", type_="foreignkey")

    # ManifestLegacyImage
    op.drop_constraint(
        op.f("fk_manifestlegacyimage_image_id_image"), "manifestlegacyimage", type_="foreignkey"
    )
    op.drop_constraint(
        op.f("fk_manifestlegacyimage_manifest_id_manifest"),
        "manifestlegacyimage",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_manifestlegacyimage_repository_id_repository"),
        "manifestlegacyimage",
        type_="foreignkey",
    )


def downgrade(op, tables, tester):
    # DerivedStorageForImage
    with op.batch_alter_table("derivedstorageforimage") as batch_op:
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
    with op.batch_alter_table("repositorytag") as batch_op:
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
    with op.batch_alter_table("torrentinfo") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_torrentinfo_storage_id_imagestorage"),
            "imagestorage",
            ["storage_id"],
            ["id"],
        )

    # TagManifest
    with op.batch_alter_table("tagmanifest") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_tagmanifest_tag_id_repositorytag"),
            "repositorytag",
            ["tag_id"],
            ["id"],
        )

    # TagManifestToManifest
    with op.batch_alter_table("tagmanifesttomanifest") as batch_op:
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
    with op.batch_alter_table("tagmanifestlabel") as batch_op:
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
    with op.batch_alter_table("tagmanifestlabelmap") as batch_op:
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
    with op.batch_alter_table("tagtorepositorytag") as batch_op:
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
    with op.batch_alter_table("image") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_image_repository_id_repository"),"repository", ["repository_id"], ["id"]
        )
        batch_op.create_foreign_key(
            op.f("fk_image_storage_id_imagestorage"), "imagestorage", ["storage_id"], ["id"]
        )

    # ManifestLegacyImage
    with op.batch_alter_table("manifestlegacyimage") as batch_op:
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
