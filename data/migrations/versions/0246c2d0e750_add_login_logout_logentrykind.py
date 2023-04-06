"""add login logout logentrykind

Revision ID: 0246c2d0e750
Revises: b2d1e4b95fc2
Create Date: 2023-04-11 14:40:57.391686

"""

# revision identifiers, used by Alembic.
revision = "0246c2d0e750"
down_revision = "b2d1e4b95fc2"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "login_success"},
            {"name": "logout_success"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.name
            == op.inline_literal("login_success") | tables.logentrykind.name
            == op.inline_literal("logout_success")
        )
    )
