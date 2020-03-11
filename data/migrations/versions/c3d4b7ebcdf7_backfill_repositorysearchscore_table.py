"""
Backfill RepositorySearchScore table.

Revision ID: c3d4b7ebcdf7
Revises: f30984525c86
Create Date: 2017-04-13 12:01:59.572775
"""

# revision identifiers, used by Alembic.
revision = "c3d4b7ebcdf7"
down_revision = "f30984525c86"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    # Add a 0 entry into the RepositorySearchScore table for each repository that isn't present
    conn = op.get_bind()
    conn.execute(
        "insert into repositorysearchscore (repository_id, score) SELECT id, 0 FROM "
        + "repository WHERE id not in (select repository_id from repositorysearchscore)"
    )


def downgrade(op, tables, tester):
    pass
