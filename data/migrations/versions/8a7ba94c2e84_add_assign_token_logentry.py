"""add assign token logentry

Revision ID: 8a7ba94c2e84
Revises: 2664723e1b4b
Create Date: 2024-07-16 11:56:54.974295

"""

# revision identifiers, used by Alembic.
revision = "8a7ba94c2e84"
down_revision = "2664723e1b4b"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "oauth_token_assigned"},
            {"name": "oauth_token_revoked"},  # May be used in a future z-stream
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.name
            == op.inline_literal("oauth_token_assigned") | tables.logentrykind.name
            == op.inline_literal("oauth_token_revoked")
        )
    )
