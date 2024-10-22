"""Add superuser and restricted user booleans

Revision ID: 87d86e3d4c2c
Revises: a32e17bfad20
Create Date: 2024-09-05 13:34:03.323911

"""

# revision identifiers, used by Alembic.
revision = "87d86e3d4c2c"
down_revision = "a32e17bfad20"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.add_column(
        "user",
        sa.Column(
            "is_superuser", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "is_restricted_user",
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "private_repos_on_push",
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.true(),
        ),
    )

    # insert new actions to log
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "add_superuser"},
            {"name": "remove_superuser"},
            {"name": "change_namespace_repo_visiblity"},
            {"name": "add_restricted_user"},
            {"name": "remove_restricted_user"},
        ],
    )


def downgrade(op, tables, tester):
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("is_superuser")
        batch_op.drop_column("is_restricted_user")
        batch_op.drop_column("private_repos_on_push")
