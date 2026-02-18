"""
Add contact_email to user table.

Revision ID: 727297654e7d
Revises: b1c2d3e4f5a6
Create Date: 2026-02-13 00:00:00.000000
"""

# revision identifiers, used by Alembic.
revision = "727297654e7d"
down_revision = "b1c2d3e4f5a6"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("user")]
    if "contact_email" not in columns:
        op.add_column("user", sa.Column("contact_email", sa.String(length=255), nullable=True))

    # ### population of test data ### #
    tester.populate_column("user", "contact_email", tester.TestDataType.String)
    # ### end population of test data ### #


def downgrade(op, tables, tester):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("user")]
    if "contact_email" in columns:
        with op.batch_alter_table("user") as batch_op:
            batch_op.drop_column("contact_email")
