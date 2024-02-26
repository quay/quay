"""insert oidc in loginservice

Revision ID: 135fd3e94615
Revises: 41d15c93c299
Create Date: 2024-02-21 09:48:54.463860

"""

# revision identifiers, used by Alembic.
revision = "135fd3e94615"
down_revision = "41d15c93c299"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.loginservice,
        [
            {"name": "oidc"},
        ],
    )
    op.create_index(
        "teamsync_config",
        "teamsync",
        ["config"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"config": "gin_trgm_ops"},
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.loginservice.delete().where(tables.loginservice.name == op.inline_literal("oidc"))
    )
    op.drop_index("teamsync_config", table_name="teamsync")
