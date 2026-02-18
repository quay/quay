"""
Cleanup old robots.

Revision ID: 5b7503aada1b
Revises: 154a822bd7e2
Create Date: 2018-05-09 17:18:52.230504
"""

# revision identifiers, used by Alembic.
revision = "5b7503aada1b"
down_revision = "154a822bd7e2"

import sqlalchemy as sa

from util.migrate.cleanup_old_robots import cleanup_old_robots


def upgrade(op, tables, tester):
    cleanup_old_robots()


def downgrade(op, tables, tester):
    # Nothing to do.
    pass
