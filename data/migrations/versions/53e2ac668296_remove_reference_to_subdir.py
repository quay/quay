"""
Remove reference to subdir.

Revision ID: 53e2ac668296
Revises: ed01e313d3cb
Create Date: 2017-03-28 15:01:31.073382
"""

# revision identifiers, used by Alembic.
import json

import logging
from alembic.script.revision import RevisionError
from alembic.util import CommandError
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "53e2ac668296"
down_revision = "ed01e313d3cb"

log = logging.getLogger(__name__)


def run_migration(migrate_function, op):
    conn = op.get_bind()
    triggers = conn.execute("SELECT id, config FROM repositorybuildtrigger")
    for trigger in triggers:
        config = json.dumps(migrate_function(json.loads(trigger[1])))
        try:
            conn.execute(
                "UPDATE repositorybuildtrigger SET config=%s WHERE id=%s", config, trigger[0]
            )
        except (RevisionError, CommandError) as e:
            log.warning("Failed to update build trigger %s with exception: ", trigger[0], e)


def upgrade(op, tables, tester):
    run_migration(delete_subdir, op)


def downgrade(op, tables, tester):
    run_migration(add_subdir, op)


def delete_subdir(config):
    """
    Remove subdir from config.
    """
    if not config:
        return config
    if "subdir" in config:
        del config["subdir"]

    return config


def add_subdir(config):
    """
    Add subdir back into config.
    """
    if not config:
        return config
    if "context" in config:
        config["subdir"] = config["context"]

    return config
