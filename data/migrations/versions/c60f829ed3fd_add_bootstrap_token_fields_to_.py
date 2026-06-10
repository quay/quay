"""add bootstrap token fields to oauthaccesstoken

Revision ID: c60f829ed3fd
Revises: c3d4e5f6a7b8
Create Date: 2026-05-23 09:02:48.037554

"""

# revision identifiers, used by Alembic.
revision = "c60f829ed3fd"
down_revision = "c3d4e5f6a7b8"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.add_column("oauthaccesstoken", sa.Column("created_by_id", sa.Integer(), nullable=True))
    op.add_column("oauthaccesstoken", sa.Column("last_accessed", sa.DateTime(), nullable=True))
    op.add_column("oauthaccesstoken", sa.Column("created", sa.DateTime(), nullable=True))

    with op.batch_alter_table("oauthaccesstoken") as batch_op:
        batch_op.create_foreign_key(
            "fk_oauthaccesstoken_created_by_id",
            "user",
            ["created_by_id"],
            ["id"],
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
        batch_op.drop_constraint("fk_oauthaccesstoken_created_by_id", type_="foreignkey")
        batch_op.drop_column("created")
        batch_op.drop_column("last_accessed")
        batch_op.drop_column("created_by_id")
