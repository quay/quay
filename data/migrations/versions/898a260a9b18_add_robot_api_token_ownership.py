"""add robot api token ownership

Revision ID: 898a260a9b18
Revises: 3cb9c1acb681
Create Date: 2026-09-17 15:10:53.391118

"""

import sqlalchemy as sa

revision = "898a260a9b18"
down_revision = "3cb9c1acb681"


def upgrade(op, tables, tester):
    with op.batch_alter_table("oauthaccesstoken") as batch_op:
        batch_op.alter_column("application_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("robot_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("creator_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_oauthaccesstoken_robot_account_id_user", "user", ["robot_account_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_oauthaccesstoken_creator_id_user", "user", ["creator_id"], ["id"]
        )
        batch_op.create_check_constraint(
            "oauthaccesstoken_application_or_robot",
            "(application_id IS NULL) != (robot_account_id IS NULL)",
        )
    op.create_index("oauthaccesstoken_robot_account_id", "oauthaccesstoken", ["robot_account_id"])
    op.bulk_insert(
        tables.logentrykind,
        [{"name": "create_robot_api_token"}, {"name": "revoke_robot_api_token"}],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name.in_(["create_robot_api_token", "revoke_robot_api_token"])
        )
    )
    op.drop_index("oauthaccesstoken_robot_account_id", table_name="oauthaccesstoken")
    with op.batch_alter_table("oauthaccesstoken") as batch_op:
        batch_op.drop_constraint("oauthaccesstoken_application_or_robot", type_="check")
        batch_op.drop_constraint("fk_oauthaccesstoken_creator_id_user", type_="foreignkey")
        batch_op.drop_constraint("fk_oauthaccesstoken_robot_account_id_user", type_="foreignkey")
        batch_op.drop_column("creator_id")
        batch_op.drop_column("robot_account_id")
        batch_op.alter_column("application_id", existing_type=sa.Integer(), nullable=False)
