"""remove unique constraint for autoprunepolicy

Revision ID: ba263f9be4a6
Revises: a32e17bfad20
Create Date: 2024-09-09 14:47:59.482614

"""

# revision identifiers, used by Alembic.
revision = "ba263f9be4a6"
down_revision = "a32e17bfad20"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    # dropping unique index and recreating the index
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
