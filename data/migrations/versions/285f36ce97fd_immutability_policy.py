"""immutability_policy

Revision ID: 285f36ce97fd
Revises: a1b2c3d4e5f6
Create Date: 2026-01-19 20:08:19.216732

"""

# revision identifiers, used by Alembic.
revision = "285f36ce97fd"
down_revision = "a1b2c3d4e5f6"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    # Create namespace immutability policy table
    op.create_table(
        "namespaceimmutabilitypolicy",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("namespace_id", sa.Integer(), nullable=False),
        sa.Column("policy", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["namespace_id"],
            ["user.id"],
            name=op.f("fk_namespaceimmutabilitypolicy_namespace_id_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_namespaceimmutabilitypolicyid")),
    )

    op.create_index(
        "namespaceimmutabilitypolicy_namespace_id",
        "namespaceimmutabilitypolicy",
        ["namespace_id"],
    )

    op.create_index(
        "namespaceimmutabilitypolicy_uuid",
        "namespaceimmutabilitypolicy",
        ["uuid"],
        unique=True,
    )

    # Create repository immutability policy table
    op.create_table(
        "repositoryimmutabilitypolicy",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("namespace_id", sa.Integer(), nullable=False),
        sa.Column("policy", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repositoryimmutabilitypolicy_repository_id_repository"),
        ),
        sa.ForeignKeyConstraint(
            ["namespace_id"],
            ["user.id"],
            name=op.f("fk_repositoryimmutabilitypolicy_namespace_id_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositoryimmutabilitypolicyid")),
    )

    op.create_index(
        "repositoryimmutabilitypolicy_repository_id",
        "repositoryimmutabilitypolicy",
        ["repository_id"],
    )

    op.create_index(
        "repositoryimmutabilitypolicy_namespace_id",
        "repositoryimmutabilitypolicy",
        ["namespace_id"],
    )

    op.create_index(
        "repositoryimmutabilitypolicy_uuid",
        "repositoryimmutabilitypolicy",
        ["uuid"],
        unique=True,
    )

    # Add log entry kinds for audit logging
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "create_immutability_policy"},
            {"name": "update_immutability_policy"},
            {"name": "delete_immutability_policy"},
        ],
    )


def downgrade(op, tables, tester):
    op.drop_table("namespaceimmutabilitypolicy")
    op.drop_table("repositoryimmutabilitypolicy")

    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name.in_(
                [
                    "create_immutability_policy",
                    "update_immutability_policy",
                    "delete_immutability_policy",
                ]
            )
        )
    )
