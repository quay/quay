"""add repository policy table

Revision ID: c437946b1c81
Revises: 8d47693829a0
Create Date: 2023-12-05 13:57:50.052108

"""

# revision identifiers, used by Alembic.
revision = "c437946b1c81"
down_revision = "8d47693829a0"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "repositorypolicy",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("policy", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repositorypolicy_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositorypolicyid")),
    )

    op.create_index(
        "repositorypolicy_repository_id",
        "repositorypolicy",
        ["repository_id"],
        unique=True,
    )


def downgrade(op, tables, tester):
    op.drop_table("repositorypolicy")
