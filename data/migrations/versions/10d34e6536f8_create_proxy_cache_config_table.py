"""create proxy_cache_config table

Revision ID: 10d34e6536f8
Revises: 909d725887d3
Create Date: 2022-01-13 16:10:10.155558

"""

# revision identifiers, used by Alembic.
revision = '10d34e6536f8'
down_revision = '909d725887d3'

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "proxy_cache_config",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("creation_date", sa.DateTime(), nullable=False),
        sa.Column("upstream_registry", sa.String(length=2048), nullable=False),
        sa.Column("upstream_registry_namespace", sa.String(length=255), nullable=False),
        sa.Column("upstream_registry_repository", sa.String(length=255), nullable=False),
        sa.Column("upstream_registry_username", sa.String(length=2048), nullable=True),
        sa.Column("upstream_registry_password", sa.String(length=2048), nullable=True),
        sa.Column("staleness_period_s", sa.Integer, server_default="0"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name=op.f("fk_proxy_cache_config_user_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_proxy_cache_config"))
    )


def downgrade(op, tables, tester):
    pass
