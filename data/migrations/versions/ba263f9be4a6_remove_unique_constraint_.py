"""remove unique constraint for autoprunepolicy

Revision ID: ba263f9be4a6
Revises: 5b8dc452f5c3
Create Date: 2024-09-09 14:47:59.482614

"""

# revision identifiers, used by Alembic.
revision = "ba263f9be4a6"
down_revision = "5b8dc452f5c3"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    bind = op.get_bind()
    # need to drop foreign key first as foreign keys in MySQL automatically create an index
    if bind.engine.name == "mysql":
        op.drop_constraint(
            "fk_namespaceautoprunepolicy_namespace_id_user",
            "namespaceautoprunepolicy",
            type_="foreignkey",
        )
        op.drop_constraint(
            "fk_repositoryautoprunepolicy_repository_id_repository",
            "repositoryautoprunepolicy",
            type_="foreignkey",
        )

    op.drop_index(
        "namespaceautoprunepolicy_namespace_id",
        "namespaceautoprunepolicy",
    )
    op.create_index(
        "namespaceautoprunepolicy_namespace_id",
        "namespaceautoprunepolicy",
        ["namespace_id"],
    )

    op.drop_index(
        "repositoryautoprunepolicy_repository_id",
        "repositoryautoprunepolicy",
    )
    op.create_index(
        "repositoryautoprunepolicy_repository_id",
        "repositoryautoprunepolicy",
        ["repository_id"],
    )

    # re-creating dropped foreign key after creating index
    if bind.engine.name == "mysql":
        op.create_foreign_key(
            "fk_namespaceautoprunepolicy_namespace_id_user",
            "namespaceautoprunepolicy",
            "user",
            ["namespace_id"],
            ["id"],
        )
        op.create_foreign_key(
            "fk_repositoryautoprunepolicy_repository_id_repository",
            "repositoryautoprunepolicy",
            "repository",
            ["repository_id"],
            ["id"],
        )


def downgrade(op, tables, tester):
    op.create_index(
        "namespaceautoprunepolicy_namespace_id",
        "namespaceautoprunepolicy",
        ["namespace_id"],
        unique=True,
    )

    op.create_index(
        "repositoryautoprunepolicy_repository_id",
        "repositoryautoprunepolicy",
        ["repository_id"],
        unique=True,
    )
