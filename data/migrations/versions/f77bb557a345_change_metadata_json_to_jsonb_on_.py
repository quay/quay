"""change metadata_json to jsonb on manifestsecuritystatus

Revision ID: f77bb557a345
Revises: c3d4e5f6a7b8
Create Date: 2026-06-16 13:44:31.119113

"""

# revision identifiers, used by Alembic.
revision = "f77bb557a345"
down_revision = "c3d4e5f6a7b8"

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade(op, tables, tester):
    bind = op.get_bind()
    if bind.engine.name == "postgresql":
        op.alter_column(
            "manifestsecuritystatus",
            "metadata_json",
            type_=postgresql.JSONB(),
            existing_type=sa.Text(),
            postgresql_using="metadata_json::jsonb",
        )


def downgrade(op, tables, tester):
    bind = op.get_bind()
    if bind.engine.name == "postgresql":
        op.alter_column(
            "manifestsecuritystatus",
            "metadata_json",
            type_=sa.Text(),
            existing_type=postgresql.JSONB(),
            postgresql_using="metadata_json::text",
        )
