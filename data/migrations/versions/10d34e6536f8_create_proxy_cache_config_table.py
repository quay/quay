"""create proxy_cache_config table

Revision ID: 10d34e6536f8
Revises: 909d725887d3
Create Date: 2022-01-13 16:10:10.155558

"""

# revision identifiers, used by Alembic.
revision = "10d34e6536f8"
down_revision = "e9f3e4dbb979"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "proxycacheconfig",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("creation_date", sa.DateTime(), nullable=False),
        sa.Column("upstream_registry", sa.String(length=2048), nullable=False),
        sa.Column("upstream_registry_username", sa.String(length=2048), nullable=True),
        sa.Column("upstream_registry_password", sa.String(length=2048), nullable=True),
        sa.Column("expiration_s", sa.Integer(), server_default="86400"),
        sa.Column(
            "insecure", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["user.id"],
            name=op.f("fk_proxy_cache_config_organization_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_proxy_cache_config")),
    )


def downgrade(op, tables, tester):
    op.drop_table("proxycacheconfig")
