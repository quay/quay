"""Add export logs auditing

Revision ID: 8e97c2cfee57
Revises: 9085e82074f2
Create Date: 2024-08-19 13:56:50.063519

"""

# revision identifiers, used by Alembic.
revision = "8e97c2cfee57"
down_revision = "9085e82074f2"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "export_logs_success"},
            {"name": "export_logs_failure"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name == op.inline_literal("export_logs_success")
        )
    )
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name == op.inline_literal("export_logs_failure")
        )
    )
