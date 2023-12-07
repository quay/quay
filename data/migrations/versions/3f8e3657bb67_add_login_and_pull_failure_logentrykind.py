"""add login and pull failure logentrykind

Revision ID: 3f8e3657bb67
Revises: 8d47693829a0
Create Date: 2023-05-06 14:21:16.580825

"""

# revision identifiers, used by Alembic.
revision = "3f8e3657bb67"
down_revision = "8d47693829a0"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "login_failure"},
            {"name": "push_repo_failed"},
            {"name": "pull_repo_failed"},
            {"name": "delete_tag_failed"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.name
            == op.inline_literal("login_failure") | tables.logentrykind.name
            == op.inline_literal("push_repo_failed") | tables.logentrykind.name
            == op.inline_literal("pull_repo_failed") | tables.logentrykind.name
            == op.inline_literal("delete_tag_failed")
        )
    )
