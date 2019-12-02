"""Run full tag backfill

Revision ID: b918abdbee43
Revises: 481623ba00ba
Create Date: 2019-03-14 13:38:03.411609

"""

# revision identifiers, used by Alembic.
revision = "b918abdbee43"
down_revision = "481623ba00ba"

import logging.config

from app import app
from peewee import JOIN, fn

from workers.tagbackfillworker import backfill_tag
from data.database import RepositoryTag, Repository, User, TagToRepositoryTag
from util.log import logfile_path

logger = logging.getLogger(__name__)


def upgrade(tables, tester, progress_reporter):
    if not app.config.get("SETUP_COMPLETE", False):
        return

    start_id = 0
    end_id = 1000
    size = 1000

    max_id = RepositoryTag.select(fn.Max(RepositoryTag.id)).scalar()
    if max_id is None:
        return

    logger.info("Found maximum ID %s" % max_id)

    while True:
        if start_id > max_id:
            break

        logger.info("Checking tag range %s - %s", start_id, end_id)
        r = list(
            RepositoryTag.select()
            .join(Repository)
            .switch(RepositoryTag)
            .join(TagToRepositoryTag, JOIN.LEFT_OUTER)
            .where(TagToRepositoryTag.id >> None)
            .where(
                RepositoryTag.hidden == False,
                RepositoryTag.id >= start_id,
                RepositoryTag.id < end_id,
            )
        )

        if len(r) < 1000 and size < 100000:
            size *= 2

        start_id = end_id
        end_id = start_id + size

        if not len(r):
            continue

        logger.info("Found %s tags to backfill", len(r))
        for index, t in enumerate(r):
            logger.info("Backfilling tag %s of %s", index, len(r))
            backfill_tag(t)


def downgrade(tables, tester, progress_reporter):
    # Nothing to do.
    pass
