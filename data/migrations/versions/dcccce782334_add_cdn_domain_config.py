"""add cdn domain config

Revision ID: dcccce782334
Revises: 2d66ad598b56
Create Date: 2022-10-19 10:16:18.374732

"""

# revision identifiers, used by Alembic.
from util.migrate import UTF8CharField

revision = 'dcccce782334'
down_revision = '2d66ad598b56'

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.add_column("user", sa.Column("cdn_config_id", sa.Integer, nullable=True))

    op.create_table(
        "cdnprovider",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("provider_name", sa.String(length=256), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cdn_providers"))
    )
    op.bulk_insert(tables.cdnprovider, [{"provider_name": "CloudFront"}])

    op.create_table(
        "cdnconfig",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("cdn_provider_id", sa.Integer, nullable=False),
        sa.Column("cdn_domain", sa.String(length=256), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cdn_config")),
        sa.ForeignKeyConstraint(
            ["cdn_provider_id"], ["cdnprovider.id"], name=op.f("fk_cdn_providers_id")
        ),
    )

    op.create_foreign_key(
        op.f("fk_cdn_config_namespace_id"),
        "user",
        "cdnconfig",
        ["cdn_config_id"],
        ["id"],
    )


def downgrade(op, tables, tester):
    op.drop_column("user", "cdn_config_id")
    op.drop_table("cdn_config")
    op.drop_table("cdn_providers")
