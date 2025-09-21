""""add_pull_statistics_tables"

Revision ID: 7fe8f09db60a
Revises: fc47c1ec019f
Create Date: 2024-12-22 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "7fe8f09db60a"
down_revision = "1623f40582ed"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    # Create TagPullStatistics table
    op.create_table(
        "tagpullstatistics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("tag_name", sa.String(length=255), nullable=False),
        sa.Column("tag_pull_count", sa.Integer(), nullable=False, default=0),
        sa.Column("last_tag_pull_date", sa.DateTime(), nullable=True),
        sa.Column("current_manifest_digest", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_tagpullstatistics_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tagpullstatistics")),
    )

    # Create indexes for TagPullStatistics
    op.create_index(
        "tagpullstatistics_repository_id",
        "tagpullstatistics",
        ["repository_id"],
        unique=False,
    )

    op.create_index(
        "tagpullstatistics_tag_name",
        "tagpullstatistics",
        ["tag_name"],
        unique=False,
    )

    op.create_index(
        "tagpullstatistics_repository_id_tag_name",
        "tagpullstatistics",
        ["repository_id", "tag_name"],
        unique=True,
    )

    op.create_index(
        "tagpullstatistics_repository_id_tag_pull_count",
        "tagpullstatistics",
        ["repository_id", "tag_pull_count"],
        unique=False,
    )

    op.create_index(
        "tagpullstatistics_repository_id_last_tag_pull_date",
        "tagpullstatistics",
        ["repository_id", "last_tag_pull_date"],
        unique=False,
    )

    # Create ManifestPullStatistics table
    op.create_table(
        "manifestpullstatistics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("manifest_digest", sa.String(length=255), nullable=False),
        sa.Column("manifest_pull_count", sa.Integer(), nullable=False, default=0),
        sa.Column("last_manifest_pull_date", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_manifestpullstatistics_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manifestpullstatistics")),
    )

    # Create indexes for ManifestPullStatistics
    op.create_index(
        "manifestpullstatistics_repository_id",
        "manifestpullstatistics",
        ["repository_id"],
        unique=False,
    )

    op.create_index(
        "manifestpullstatistics_manifest_digest",
        "manifestpullstatistics",
        ["manifest_digest"],
        unique=False,
    )

    op.create_index(
        "manifestpullstatistics_repository_id_manifest_digest",
        "manifestpullstatistics",
        ["repository_id", "manifest_digest"],
        unique=True,
    )

    op.create_index(
        "manifestpullstatistics_repository_id_manifest_pull_count",
        "manifestpullstatistics",
        ["repository_id", "manifest_pull_count"],
        unique=False,
    )

    op.create_index(
        "manifestpullstatistics_repository_id_last_manifest_pull_date",
        "manifestpullstatistics",
        ["repository_id", "last_manifest_pull_date"],
        unique=False,
    )


def downgrade(op, tables, tester):
    # Drop ManifestPullStatistics indexes
    op.drop_index(
        "manifestpullstatistics_repository_id_last_manifest_pull_date",
        table_name="manifestpullstatistics",
    )
    op.drop_index(
        "manifestpullstatistics_repository_id_manifest_pull_count",
        table_name="manifestpullstatistics",
    )
    op.drop_index(
        "manifestpullstatistics_repository_id_manifest_digest",
        table_name="manifestpullstatistics",
    )
    op.drop_index(
        "manifestpullstatistics_manifest_digest",
        table_name="manifestpullstatistics",
    )
    op.drop_index(
        "manifestpullstatistics_repository_id",
        table_name="manifestpullstatistics",
    )

    # Drop TagPullStatistics indexes
    op.drop_index(
        "tagpullstatistics_repository_id_last_tag_pull_date",
        table_name="tagpullstatistics",
    )
    op.drop_index(
        "tagpullstatistics_repository_id_tag_pull_count",
        table_name="tagpullstatistics",
    )
    op.drop_index(
        "tagpullstatistics_repository_id_tag_name",
        table_name="tagpullstatistics",
    )
    op.drop_index(
        "tagpullstatistics_tag_name",
        table_name="tagpullstatistics",
    )
    op.drop_index(
        "tagpullstatistics_repository_id",
        table_name="tagpullstatistics",
    )

    # Drop tables
    op.drop_table("manifestpullstatistics")
    op.drop_table("tagpullstatistics")
