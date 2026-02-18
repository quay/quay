"""recreate namespacegeorestriction table

Revision ID: eb30ce41b52d
Revises: 15f06d00c4b3
Create Date: 2026-02-19 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "eb30ce41b52d"
down_revision = "15f06d00c4b3"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "namespacegeorestriction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("namespace_id", sa.Integer(), nullable=False),
        sa.Column("added", sa.DateTime(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("unstructured_json", sa.Text(), nullable=False),
        sa.Column("restricted_region_iso_code", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["namespace_id"],
            ["user.id"],
            name=op.f("fk_namespacegeorestriction_namespace_id_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_namespacegeorestriction")),
    )
    op.create_index(
        "namespacegeorestriction_namespace_id",
        "namespacegeorestriction",
        ["namespace_id"],
        unique=False,
    )
    op.create_index(
        "namespacegeorestriction_namespace_id_restricted_region_iso_code",
        "namespacegeorestriction",
        ["namespace_id", "restricted_region_iso_code"],
        unique=True,
    )
    op.create_index(
        "namespacegeorestriction_restricted_region_iso_code",
        "namespacegeorestriction",
        ["restricted_region_iso_code"],
        unique=False,
    )


def downgrade(op, tables, tester):
    op.drop_table("namespacegeorestriction")
