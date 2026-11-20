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
            tables.logentrykind.c.name.in_(
                [
                    "org_create",
                    "org_delete",
                    "org_change_email",
                    "org_change_invoicing",
                    "org_change_tag_expiration",
                    "org_change_name",
                    "user_create",
                    "user_delete",
                    "user_disable",
                    "user_enable",
                    "user_change_email",
                    "user_change_password",
                    "user_change_name",
                    "user_change_invoicing",
                    "user_change_tag_expiration",
                    "user_change_metadata",
                    "user_generate_client_key",
                ]
            )
        )
    )
