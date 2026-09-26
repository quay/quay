"""add workload identity audit log kinds

Revision ID: 8fd6edfc06db
Revises: 9fa37f66a9b6
Create Date: 2026-09-09 19:21:38.130579

"""

# revision identifiers, used by Alembic.
revision = "8fd6edfc06db"
down_revision = "9fa37f66a9b6"


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "workload_identity_token_exchange"},
            {"name": "workload_identity_token_exchange_failed"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name.in_(
                [
                    "workload_identity_token_exchange",
                    "workload_identity_token_exchange_failed",
                ]
            )
        )
    )
