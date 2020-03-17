"""
Run full tag backfill.

Revision ID: b918abdbee43
Revises: 481623ba00ba
Create Date: 2019-03-14 13:38:03.411609
"""

# revision identifiers, used by Alembic.
revision = "b918abdbee43"
down_revision = "481623ba00ba"

import logging.config

from app import app
from data.database import TagManifest

from util.log import logfile_path

logger = logging.getLogger(__name__)


def upgrade(op, tables, tester):
    # Backfill migration removed.
    if not tester.is_testing:
        assert TagManifest.select().count() == 0


def downgrade(op, tables, tester):
    # Nothing to do.
    pass
