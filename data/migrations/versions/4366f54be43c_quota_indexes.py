"""add indexes to quotanamespacesize and quotarepositorysize tables

Revision ID: 4366f54be43c
Revises: b82361fba1cd
Create Date: 2023-09-27 16:34:30.570757

"""

# revision identifiers, used by Alembic.
revision = "4366f54be43c"
down_revision = "b82361fba1cd"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_index(
        "quotanamespacesize_namespace_user_id",
        "quotanamespacesize",
        ["namespace_user_id"],
        unique=True,
    )

    # Index used by the quotatotalworker to find the next namespace to backfill
    op.create_index(
        "quotanamespacesize_backfill_start_ms",
        "quotanamespacesize",
        ["backfill_start_ms"],
        unique=False,
    )

    # Index used by future API's for quick sorting of the largest namespaces
    op.create_index(
        "quotanamespacesize_size_bytes", "quotanamespacesize", ["size_bytes"], unique=False
    )

    op.create_index(
        "quotarepositorysize_repository_id", "quotarepositorysize", ["repository_id"], unique=True
    )

    # Index used by future API's for quick sorting of the largest repositories
    op.create_index(
        "quotarepositorysize_size_bytes", "quotarepositorysize", ["size_bytes"], unique=False
    )


def downgrade(op, tables, tester):
    bind = op.get_bind()
    # MySQL needs an index on foreign key columns, so the foreign keys have to be dropped before
    # the indexes backing them and re-created afterwards.
    if bind.engine.name == "mysql":
        op.drop_constraint(
            "fk_quotanamespacesize_namespace_user_id_user",
            "quotanamespacesize",
            type_="foreignkey",
        )
        op.drop_constraint(
            "fk_quotarepositorysize_repository_id_repository",
            "quotarepositorysize",
            type_="foreignkey",
        )

    op.drop_index("quotanamespacesize_namespace_user_id", table_name="quotanamespacesize")
    op.drop_index("quotanamespacesize_backfill_start_ms", table_name="quotanamespacesize")
    op.drop_index("quotanamespacesize_size_bytes", table_name="quotanamespacesize")
    op.drop_index("quotarepositorysize_repository_id", table_name="quotarepositorysize")
    op.drop_index("quotarepositorysize_size_bytes", table_name="quotarepositorysize")

    if bind.engine.name == "mysql":
        op.create_foreign_key(
            "fk_quotanamespacesize_namespace_user_id_user",
            "quotanamespacesize",
            "user",
            ["namespace_user_id"],
            ["id"],
        )
        op.create_foreign_key(
            "fk_quotarepositorysize_repository_id_repository",
            "quotarepositorysize",
            "repository",
            ["repository_id"],
            ["id"],
        )
