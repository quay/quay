"""“quota-v2”

Revision ID: f0875fbc7c7a
Revises: b2d1e4b95fc2
Create Date: 2023-01-25 10:48:02.386665

"""

# revision identifiers, used by Alembic.
revision = "f0875fbc7c7a"
down_revision = "b2d1e4b95fc2"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "namespacesize",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("namespace_user_id", sa.Integer, nullable=False),
        sa.Column("size_bytes", sa.NUMERIC, nullable=False),
        sa.Column("summed_until_ms", sa.BIGINT, nullable=True),
        sa.Column("running", sa.Boolean, nullable=False, default=False),
        sa.ForeignKeyConstraint(
            ["namespace_user_id"],
            ["user.id"],
            name=op.f("fk_repositorysize_namespace_user_id_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_namespacesizeid")),
    )

    op.add_column(
        "repositorysize",
        sa.Column("summed_until_ms", sa.BIGINT, nullable=True),
    )
    op.add_column(
        "repositorysize",
        sa.Column("running", sa.Boolean, nullable=False, default=False),
    )


def downgrade(op, tables, tester):
    pass
