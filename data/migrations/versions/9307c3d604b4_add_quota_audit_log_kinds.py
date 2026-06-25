"""add_quota_audit_log_kinds

Revision ID: 9307c3d604b4
Revises: 7078c84d14e8
Create Date: 2025-12-08 10:23:13.342588

"""

# revision identifiers, used by Alembic.
revision = "9307c3d604b4"
down_revision = "7078c84d14e8"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "org_create_quota"},
            {"name": "org_change_quota"},
            {"name": "org_delete_quota"},
            {"name": "org_create_quota_limit"},
            {"name": "org_change_quota_limit"},
            {"name": "org_delete_quota_limit"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name.in_(
                [
                    "org_create_quota",
                    "org_change_quota",
                    "org_delete_quota",
                    "org_create_quota_limit",
                    "org_change_quota_limit",
                    "org_delete_quota_limit",
                ]
            )
        )
    )
