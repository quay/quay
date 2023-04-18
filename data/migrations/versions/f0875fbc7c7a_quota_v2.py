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
        "quotanamespacesize",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("namespace_user_id", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("backfill_start_ms", sa.BigInteger(), nullable=True),
        sa.Column(
            "backfill_complete",
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
        sa.ForeignKeyConstraint(
            ["namespace_user_id"],
            ["user.id"],
            name=op.f("fk_quotanamespacesize_namespace_user_id_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quotanamespacesizeid")),
    )

    op.create_table(
        "quotarepositorysize",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("backfill_start_ms", sa.BigInteger(), nullable=True),
        sa.Column(
            "backfill_complete",
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_quotarepositorysize_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quotarepositorysizeid")),
    )


def downgrade(op, tables, tester):
    op.drop_table("quotanamespacesize")
    op.drop_table("quotarepositorysize")
