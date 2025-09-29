""""add_pull_statistics_tables"

Revision ID: 52af6c5cddc1
Revises: fc47c1ec019f
Create Date: 2024-09-29 12:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "52af6c5cddc1"
down_revision = "fc47c1ec019f"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    # Create TagPullStatistics table
    op.create_table(
        "tagpullstatistics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("tag_name", sa.String(length=255), nullable=False),
        sa.Column("tag_pull_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "last_tag_pull_date",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("current_manifest_digest", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_tagpullstatistics_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tagpullstatistics_id")),
    )

    # Add composite unique constraint for (repository_id, tag_name)
    op.create_index(
        op.f("ix_tagpullstatistics_repository_id_tag_name"),
        "tagpullstatistics",
        ["repository_id", "tag_name"],
        unique=True,
    )

    # Add indexes for query performance
    op.create_index(
        op.f("ix_tagpullstatistics_last_tag_pull_date"), "tagpullstatistics", ["last_tag_pull_date"]
    )
    op.create_index(
        op.f("ix_tagpullstatistics_tag_pull_count"), "tagpullstatistics", ["tag_pull_count"]
    )
    op.create_index(
        op.f("ix_tagpullstatistics_repository_id"), "tagpullstatistics", ["repository_id"]
    )

    # Create ManifestPullStatistics table
    op.create_table(
        "manifestpullstatistics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("manifest_digest", sa.String(length=255), nullable=False),
        sa.Column("manifest_pull_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "last_manifest_pull_date",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_manifestpullstatistics_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manifestpullstatistics_id")),
    )

    # Add composite unique constraint for (repository_id, manifest_digest)
    op.create_index(
        op.f("ix_manifestpullstatistics_repository_id_manifest_digest"),
        "manifestpullstatistics",
        ["repository_id", "manifest_digest"],
        unique=True,
    )

    # Add indexes for query performance
    op.create_index(
        op.f("ix_manifestpullstatistics_last_manifest_pull_date"),
        "manifestpullstatistics",
        ["last_manifest_pull_date"],
    )
    op.create_index(
        op.f("ix_manifestpullstatistics_manifest_pull_count"),
        "manifestpullstatistics",
        ["manifest_pull_count"],
    )
    op.create_index(
        op.f("ix_manifestpullstatistics_repository_id"), "manifestpullstatistics", ["repository_id"]
    )


def downgrade(op, tables, tester):
    # Drop tables in reverse order
    op.drop_table("manifestpullstatistics")
    op.drop_table("tagpullstatistics")
