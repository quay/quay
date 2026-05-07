"""Add helm_chart_metadata table

Revision ID: a7b8c9d0e1f2
Revises: c3d4e5f6a7b8
Create Date: 2026-04-04 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "a7b8c9d0e1f2"
down_revision = "c3d4e5f6a7b8"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "helmchartmetadata",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("manifest_id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("chart_name", sa.String(length=255), nullable=False),
        sa.Column("chart_version", sa.String(length=255), nullable=False),
        sa.Column("app_version", sa.String(length=255), nullable=True),
        sa.Column("api_version", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("kube_version", sa.String(length=255), nullable=True),
        sa.Column("chart_type", sa.String(length=32), nullable=True),
        sa.Column("home", sa.String(length=2048), nullable=True),
        sa.Column("icon_url", sa.String(length=2048), nullable=True),
        sa.Column("deprecated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sources", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("maintainers", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("chart_dependencies", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("keywords", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("annotations", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("chart_yaml", sa.Text(), nullable=False),
        sa.Column("readme", sa.Text(), nullable=True),
        sa.Column("values_yaml", sa.Text(), nullable=True),
        sa.Column("values_schema_json", sa.Text(), nullable=True),
        sa.Column("provenance", sa.Text(), nullable=True),
        sa.Column("provenance_key_id", sa.String(length=64), nullable=True),
        sa.Column("provenance_hash_algorithm", sa.String(length=32), nullable=True),
        sa.Column("provenance_signature_date", sa.String(length=64), nullable=True),
        sa.Column("icon_data", sa.Text(), nullable=True),
        sa.Column("icon_media_type", sa.String(length=128), nullable=True),
        sa.Column("file_tree", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("image_references", sa.Text(), nullable=False, server_default="[]"),
        sa.Column(
            "extraction_status", sa.String(length=32), nullable=False, server_default="pending"
        ),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["manifest_id"],
            ["manifest.id"],
            name=op.f("fk_helmchartmetadata_manifest_id_manifest"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_helmchartmetadata_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_helmchartmetadata")),
    )

    op.create_index(
        "helmchartmetadata_manifest_id",
        "helmchartmetadata",
        ["manifest_id"],
        unique=True,
    )
    op.create_index(
        "helmchartmetadata_repository_id",
        "helmchartmetadata",
        ["repository_id"],
        unique=False,
    )
    op.create_index(
        "helmchartmetadata_extraction_status",
        "helmchartmetadata",
        ["extraction_status"],
        unique=False,
    )

    op.create_table(
        "helmrepoindexconfig",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tag_pattern", sa.String(length=256), nullable=True),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_helmrepoindexconfig_repository_id_repository"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_helmrepoindexconfig")),
    )

    op.create_index(
        "helmrepoindexconfig_repository_id",
        "helmrepoindexconfig",
        ["repository_id"],
        unique=True,
    )


def downgrade(op, tables, tester):
    op.drop_table("helmrepoindexconfig")
    op.drop_table("helmchartmetadata")
