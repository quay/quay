"""
Add contact_email to user table (early).

Revision ID: 154a822bd7e2
Revises: 224ce4c72c2f
Create Date: 2026-02-18 00:00:00.000000

This migration is positioned early in the chain (before cleanup_old_robots)
to ensure the contact_email column exists before any migration that queries
the User model via Peewee. Peewee generates SQL with all model fields,
so the column must exist in the database before those queries run.
"""

# revision identifiers, used by Alembic.
revision = "154a822bd7e2"
down_revision = "224ce4c72c2f"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("user")]
    if "contact_email" not in columns:
        op.add_column("user", sa.Column("contact_email", sa.String(length=255), nullable=True))


def downgrade(op, tables, tester):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("user")]
    if "contact_email" in columns:
        with op.batch_alter_table("user") as batch_op:
            batch_op.drop_column("contact_email")
