"""add oauth api token metadata and audit log kinds

Revision ID: d064a4f00d4a
Revises: b1a79fa8e630
Create Date: 2026-07-07 20:20:50.272222

"""

# revision identifiers, used by Alembic.
revision = "d064a4f00d4a"
down_revision = "b1a79fa8e630"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.add_column("oauthaccesstoken", sa.Column("last_accessed", sa.DateTime(), nullable=True))
    op.add_column("oauthaccesstoken", sa.Column("created", sa.DateTime(), nullable=True))
    op.create_index(
        "oauthaccesstoken_application_id_last_accessed",
        "oauthaccesstoken",
        ["application_id", "last_accessed"],
        unique=False,
    )

    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "create_oauth_api_token"},
            {"name": "revoke_oauth_api_token"},
        ],
    )

    tester.populate_column("oauthaccesstoken", "last_accessed", tester.TestDataType.DateTime)
    tester.populate_column("oauthaccesstoken", "created", tester.TestDataType.DateTime)


def downgrade(op, tables, tester):
    op.drop_index(
        "oauthaccesstoken_application_id_last_accessed",
        table_name="oauthaccesstoken",
    )

    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name.in_(
                [
                    "create_oauth_api_token",
                    "revoke_oauth_api_token",
                ]
            )
        )
    )

    with op.batch_alter_table("oauthaccesstoken") as batch_op:
        batch_op.drop_column("created")
        batch_op.drop_column("last_accessed")
