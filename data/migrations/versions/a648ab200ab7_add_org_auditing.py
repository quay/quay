"""add org auditing

Revision ID: a648ab200ab7
Revises: f0875fbc7c7a
Create Date: 2023-04-27 18:00:59.985970

"""

# revision identifiers, used by Alembic.
import sqlalchemy as sa

revision = "a648ab200ab7"
down_revision = "f0875fbc7c7a"


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "org_create"},
            {"name": "org_delete"},
            {"name": "org_change_email"},
            {"name": "org_change_invoicing"},
            {"name": "org_change_tag_expiration"},
            {"name": "org_change_name"},
            {"name": "user_create"},
            {"name": "user_delete"},
            {"name": "user_disable"},
            {"name": "user_enable"},
            {"name": "user_change_email"},
            {"name": "user_change_password"},
            {"name": "user_change_name"},
            {"name": "user_change_invoicing"},
            {"name": "user_change_tag_expiration"},
            {"name": "user_change_metadata"},
            {"name": "user_generate_client_key"},
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
            == op.inline_literal("org_change_tag_expiration") | tables.logentrykind.name
            == op.inline_literal("org_change_name") | tables.logentrykind.name
            == op.inline_literal("user_create") | tables.logentrykind.name
            == op.inline_literal("user_delete") | tables.logentrykind.name
            == op.inline_literal("user_disable") | tables.logentrykind.name
            == op.inline_literal("user_enable") | tables.logentrykind.name
            == op.inline_literal("user_change_email") | tables.logentrykind.name
            == op.inline_literal("user_change_password") | tables.logentrykind.name
            == op.inline_literal("user_change_name") | tables.logentrykind.name
            == op.inline_literal("user_change_invoicing") | tables.logentrykind.name
            == op.inline_literal("user_change_tag_expiration") | tables.logentrykind.name
            == op.inline_literal("user_change_metadata") | tables.logentrykind.name
            == op.inline_literal("user_generate_client_key")
        )
    )
