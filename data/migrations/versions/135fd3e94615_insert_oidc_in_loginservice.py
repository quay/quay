"""insert oidc in loginservice

Revision ID: 135fd3e94615
Revises: b4da5b09c8df
Create Date: 2024-02-21 09:48:54.463860

"""

# revision identifiers, used by Alembic.
revision = "135fd3e94615"
down_revision = "b4da5b09c8df"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.loginservice,
        [
            {"name": "oidc"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.loginservice.delete().where(tables.loginservice.name == op.inline_literal("oidc"))
    )
