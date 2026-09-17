"""add robot API scopes log entry kind

Revision ID: 3cb9c1acb681
Revises: 9fa37f66a9b6
Create Date: 2026-09-15 20:05:12.730436

"""

# revision identifiers, used by Alembic.
revision = "3cb9c1acb681"
down_revision = "9fa37f66a9b6"


def upgrade(op, tables, tester):
    op.bulk_insert(tables.logentrykind, [{"name": "update_robot_api_scopes"}])


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(tables.logentrykind.c.name == "update_robot_api_scopes")
    )
