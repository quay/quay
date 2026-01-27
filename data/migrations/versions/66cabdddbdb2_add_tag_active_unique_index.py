"""add_tag_active_unique_index

Revision ID: 66cabdddbdb2
Revises: 285f36ce97fd
Create Date: 2026-01-27 10:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "66cabdddbdb2"
down_revision = "285f36ce97fd"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    # Partial unique indexes are PostgreSQL-specific. SQLite ignores the WHERE clause
    # and creates a regular unique index, which would break tag expiration.
    bind = op.get_bind()
    if bind.engine.name != "postgresql":
        return

    op.create_index(
        "tag_repository_id_name_active_unique",
        "tag",
        ["repository_id", "name"],
        unique=True,
        postgresql_where=sa.text("lifetime_end_ms IS NULL"),
    )


def downgrade(op, tables, tester):
    bind = op.get_bind()
    if bind.engine.name != "postgresql":
        return

    op.drop_index("tag_repository_id_name_active_unique", table_name="tag")
