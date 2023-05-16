"""add permanently delete tag log entry kind

Revision ID: 8cf90670bf38
Revises: 43fea47d641f
Create Date: 2023-05-15 16:45:59.245515

"""

# revision identifiers, used by Alembic.
revision = '8cf90670bf38'
down_revision = '43fea47d641f'

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "permanently_delete_tag"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name == op.inline_literal("permanently_delete_tag")
        )
    )
