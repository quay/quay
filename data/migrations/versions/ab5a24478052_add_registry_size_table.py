"""“add_registry_size_table”

Revision ID: ab5a24478052
Revises: 0246c2d0e750
Create Date: 2023-03-07 09:15:45.681530

"""

# revision identifiers, used by Alembic.
revision = "ab5a24478052"
down_revision = "0246c2d0e750"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "quotaregistrysize",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "running", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()
        ),
        sa.Column("queued", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()),
        sa.Column(
            "completed_ms",
            sa.BigInteger(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quotaregistrysizeid")),
    )


def downgrade(op, tables, tester):
    op.drop_table("quotaregistrysize")
