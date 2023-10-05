"""“autopruning”

Revision ID: 222debc16e18
Revises: 4366f54be43c
Create Date: 2023-08-15 15:46:50.280955

"""

# revision identifiers, used by Alembic.
revision = "222debc16e18"
down_revision = "4366f54be43c"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "namespaceautoprunepolicy",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("namespace_id", sa.Integer(), nullable=False),
        sa.Column("policy", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["namespace_id"],
            ["user.id"],
            name=op.f("fk_namespaceautoprunepolicy_namespace_id_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_namespaceautoprunepolicyid")),
    )

    op.create_index(
        "namespaceautoprunepolicy_namespace_id",
        "namespaceautoprunepolicy",
        ["namespace_id"],
        unique=True,
    )

    op.create_index(
        "namespaceautoprunepolicy_uuid",
        "namespaceautoprunepolicy",
        ["uuid"],
        unique=True,
    )

    op.create_table(
        "autoprunetaskstatus",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("namespace_id", sa.Integer(), nullable=False),
        sa.Column("last_ran_ms", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["namespace_id"], ["user.id"], name=op.f("fk_autoprunetaskstatus_namespace_id_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_autoprunetaskstatusid")),
    )

    op.create_index(
        "autoprunetaskstatus_namespace_id",
        "autoprunetaskstatus",
        ["namespace_id"],
        unique=True,
    )

    op.create_index(
        "autoprunetaskstatus_last_ran_ms",
        "autoprunetaskstatus",
        ["last_ran_ms"],
        unique=False,
    )


def downgrade(op, tables, tester):
    op.drop_table("namespaceautoprunepolicy")
    op.drop_table("autoprunetaskstatus")
