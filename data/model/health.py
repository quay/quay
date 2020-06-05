import logging

from data.database import TeamRole, validate_database_url

logger = logging.getLogger(__name__)


def check_health(app_config):
    # Attempt to connect to the database first. If the DB is not responding,
    # using the validate_database_url will timeout quickly, as opposed to
    # making a normal connect which will just hang (thus breaking the health
    # check).
    try:
        validate_database_url(app_config["DB_URI"], {}, connect_timeout=3)
    except Exception as ex:
        return (False, "Could not connect to the database: %s" % str(ex))

    # We will connect to the db, check that it contains some team role kinds
    try:
        okay = bool(list(TeamRole.select().limit(1)))
        return (okay, "Could not connect to the database" if not okay else None)
    except Exception as ex:
        return (False, "Could not connect to the database: %s" % str(ex))
