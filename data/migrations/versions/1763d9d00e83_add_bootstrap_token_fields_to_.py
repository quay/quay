"""add bootstrap token fields to oauthaccesstoken

Revision ID: 1763d9d00e83
Revises: c3d4e5f6a7b8
Create Date: 2026-06-12 20:18:35.819774

"""

# revision identifiers, used by Alembic.
revision = "1763d9d00e83"
down_revision = "c3d4e5f6a7b8"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.add_column("oauthaccesstoken", sa.Column("last_accessed", sa.DateTime(), nullable=True))
    op.add_column("oauthaccesstoken", sa.Column("created", sa.DateTime(), nullable=True))

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
