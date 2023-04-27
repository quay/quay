"""add org auditing

Revision ID: a648ab200ab7
Revises: b2d1e4b95fc2
Create Date: 2023-04-27 18:00:59.985970

"""

# revision identifiers, used by Alembic.
revision = 'a648ab200ab7'
down_revision = 'b2d1e4b95fc2'

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "org_create"},
            {"name": "org_delete"},
            {"name": "org_change_email"},
            {"name": "org_change_invoicing"},
            {"name": "org_change_tag_expiration"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.name
            == op.inline_literal("org_create") | tables.logentrykind.name
            == op.inline_literal("org_delete") | tables.logentrykind.name
            == op.inline_literal("org_change_email") | tables.logentrykind.name
            == op.inline_literal("org_change_invoicing") | tables.logentrykind.name
            == op.inline_literal("org_change_tag_expiration")
        )
    )
