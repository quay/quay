"""
Remove unique from TagManifestToManifest.

Revision ID: 13411de1c0ff
Revises: 654e6df88b71
Create Date: 2018-08-19 23:30:24.969549
"""

# revision identifiers, used by Alembic.
revision = "13411de1c0ff"
down_revision = "654e6df88b71"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    # Note: Because of a restriction in MySQL, we cannot simply remove the index and re-add
    # it without the unique=False, nor can we simply alter the index. To make it work, we'd have to
    # remove the primary key on the field, so instead we simply drop the table entirely and
    # recreate it with the modified index. The backfill will re-fill this in.
    op.drop_table("tagmanifesttomanifest")

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
    op.create_index(
        "tagmanifesttomanifest_manifest_id", "tagmanifesttomanifest", ["manifest_id"], unique=False
    )
    op.create_index(
        "tagmanifesttomanifest_tag_manifest_id",
        "tagmanifesttomanifest",
        ["tag_manifest_id"],
        unique=True,
    )

    tester.populate_table(
        "tagmanifesttomanifest",
        [
            ("manifest_id", tester.TestDataType.Foreign("manifest")),
            ("tag_manifest_id", tester.TestDataType.Foreign("tagmanifest")),
        ],
    )


def downgrade(op, tables, tester):
    pass
