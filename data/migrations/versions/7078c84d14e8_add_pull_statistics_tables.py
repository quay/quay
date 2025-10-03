"""add_pull_statistics_tables

Revision ID: 7078c84d14e8
Revises: 1623f40582ed
Create Date: 2024-09-30 12:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "7078c84d14e8"
down_revision = "1623f40582ed"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    # Create TagPullStatistics table
    op.create_table(
        "tagpullstatistics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("tag_name", sa.String(length=255), nullable=False),
        sa.Column("tag_pull_count", sa.BigInteger(), nullable=False),
        sa.Column("last_tag_pull_date", sa.DateTime(), nullable=False),
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
        "tagpullstatistics_repository_id_tag_name",
        "tagpullstatistics",
        ["repository_id", "tag_name"],
        unique=True,
    )

    # Create ManifestPullStatistics table
    op.create_table(
        "manifestpullstatistics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("manifest_digest", sa.String(length=255), nullable=False),
        sa.Column("manifest_pull_count", sa.BigInteger(), nullable=False),
        sa.Column("last_manifest_pull_date", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_manifestpullstatistics_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manifestpullstatistics")),
    )

    # Create indexes for ManifestPullStatistics
    op.create_index(
        "manifestpullstatistics_repository_id_manifest_digest",
        "manifestpullstatistics",
        ["repository_id", "manifest_digest"],
        unique=True,
    )


def downgrade(op, tables, tester):
    # Drop ManifestPullStatistics indexes
    op.drop_index(
        "manifestpullstatistics_repository_id_manifest_digest",
        table_name="manifestpullstatistics",
    )

    # Drop TagPullStatistics indexes
    op.drop_index(
        "tagpullstatistics_repository_id_tag_name",
        table_name="tagpullstatistics",
    )

    # Drop tables
    op.drop_table("manifestpullstatistics")
    op.drop_table("tagpullstatistics")
