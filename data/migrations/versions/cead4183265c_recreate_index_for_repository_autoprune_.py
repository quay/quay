"""recreate index for repository autoprune policy

Revision ID: cead4183265c
Revises: 135fd3e94615
Create Date: 2024-03-05 23:45:05.154796

"""

# revision identifiers, used by Alembic.
revision = "cead4183265c"
down_revision = "135fd3e94615"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    # Note: In order to set unique=False, we cannot simply alter index. We need to drop the corresponding foreign key constraint first
    # and then drop the index and recreate it.
    with op.batch_alter_table("repositoryautoprunepolicy") as batch_op:
        batch_op.drop_constraint(
            op.f("fk_repositoryautoprunepolicy_namespace_id_user"),
            type_="foreignkey",
        )
    op.drop_index("repositoryautoprunepolicy_namespace_id", table_name="repositoryautoprunepolicy")

    with op.batch_alter_table("repositoryautoprunepolicy") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_repositoryautoprunepolicy_namespace_id_user"),
            "user",
            ["namespace_id"],
            ["id"],
        )
    op.create_index(
        "repositoryautoprunepolicy_namespace_id",
        "repositoryautoprunepolicy",
        ["namespace_id"],
        unique=False,
    )


def downgrade(op, tables, tester):
    with op.batch_alter_table("repositoryautoprunepolicy") as batch_op:
        batch_op.drop_constraint(
            op.f("fk_repositoryautoprunepolicy_namespace_id_user"),
            type_="foreignkey",
        )
    op.drop_index("repositoryautoprunepolicy_namespace_id", table_name="repositoryautoprunepolicy")

    with op.batch_alter_table("repositoryautoprunepolicy") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_repositoryautoprunepolicy_namespace_id_user"),
            "user",
            ["namespace_id"],
            ["id"],
        )
    op.create_index(
        "repositoryautoprunepolicy_namespace_id",
        "repositoryautoprunepolicy",
        ["namespace_id"],
        unique=True,
    )
