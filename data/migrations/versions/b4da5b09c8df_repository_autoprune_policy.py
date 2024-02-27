"""repository autoprune policy

Revision ID: b4da5b09c8df
Revises: 41d15c93c299
Create Date: 2024-02-05 10:47:32.172623

"""

# revision identifiers, used by Alembic.
revision = "b4da5b09c8df"
down_revision = "41d15c93c299"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "repositoryautoprunepolicy",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("namespace_id", sa.Integer(), nullable=False),
        sa.Column("policy", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repositoryautoprunepolicy_repository_id_repository"),
        ),
        sa.ForeignKeyConstraint(
            ["namespace_id"],
            ["user.id"],
            name=op.f("fk_repositoryautoprunepolicy_namespace_id_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositoryautoprunepolicyid")),
    )

    op.create_index(
        "repositoryautoprunepolicy_repository_id",
        "repositoryautoprunepolicy",
        ["repository_id"],
        unique=True,
    )

    op.create_index(
        "repositoryautoprunepolicy_namespace_id",
        "repositoryautoprunepolicy",
        ["namespace_id"],
        unique=True,
    )

    op.create_index(
        "repositoryautoprunepolicy_uuid",
        "repositoryautoprunepolicy",
        ["uuid"],
        unique=True,
    )

    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "create_repository_autoprune_policy"},
            {"name": "update_repository_autoprune_policy"},
            {"name": "delete_repository_autoprune_policy"},
        ],
    )


def downgrade(op, tables, tester):
    op.drop_table("repositoryautoprunepolicy")

    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name
            == op.inline_literal("create_repository_autoprune_policy") | tables.logentrykind.c.name
            == op.inline_literal("update_repository_autoprune_policy") | tables.logentrykind.c.name
            == op.inline_literal("delete_repository_autoprune_policy")
        )
    )
