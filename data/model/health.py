import logging
from contextlib import contextmanager

from data.database import TeamRole, db, validate_database_url

logger = logging.getLogger(__name__)


@contextmanager
def sql_timeout(app_config, database, timeout):
    # Apply the context manager only if PostgreSQL is used as db schema
    if "postgresql" in app_config["DB_URI"]:
        logger.debug("Checking for existence of team roles, timeout 5000 ms.")
        database.execute_sql("SET statement_timeout=%s;", (timeout,))
        try:
            yield database
        finally:
            database.execute_sql("SET statement_timeout=%s;", (0,))
    else:
        logger.debug("Checking for existence of team roles.")
        try:
            yield database
        finally:
            pass


def check_health(app_config):
    # Attempt to connect to the database first. If the DB is not responding,
    # using the validate_database_url will timeout quickly, as opposed to
    # making a normal connect which will just hang (thus breaking the health
    # check).
    try:
        logger.debug("Validating database connection.")
        validate_database_url(
            app_config["DB_URI"], app_config["DB_CONNECTION_ARGS"], connect_timeout=3
        )
    except Exception as ex:
        return (False, "Could not connect to the database: %s" % str(ex))

    # We will connect to the db, check that it contains some team role kinds
    try:
        with sql_timeout(app_config, db, 5000):
            okay = bool(list(TeamRole.select().limit(1)))
            return (okay, "Could not execute query, timeout reached" if not okay else None)
    except Exception as ex:
        return (False, "Could not connect to the database: %s" % str(ex))
