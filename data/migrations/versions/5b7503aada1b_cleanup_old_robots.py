"""
Cleanup old robots.

Revision ID: 5b7503aada1b
Revises: 224ce4c72c2f
Create Date: 2018-05-09 17:18:52.230504
"""

# revision identifiers, used by Alembic.
revision = "5b7503aada1b"
down_revision = "224ce4c72c2f"

import sqlalchemy as sa

from util.migrate.cleanup_old_robots import cleanup_old_robots


def upgrade(op, tables, tester):
    cleanup_old_robots()


def downgrade(op, tables, tester):
    # Nothing to do.
    pass
