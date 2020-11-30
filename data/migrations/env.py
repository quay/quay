import logging
import os

from urllib.parse import unquote

from alembic import context, op as alembic_op
from alembic.script.revision import ResolutionError
from alembic.util import CommandError
from peewee import SqliteDatabase
from sqlalchemy import create_engine

from app import app
from data.database import all_models, db, LEGACY_INDEX_MAP
from data.migrations.tester import NoopTester, PopulateTestDataTester
from data.model.sqlalchemybridge import gen_sqlalchemy_metadata
from release import GIT_HEAD, REGION, SERVICE
from util.morecollections import AttrDict


logger = logging.getLogger(__name__)


# Alembic's configuration
config = context.config


# Alembic is designed to be used with SQL Alchemy. These steps convert the schema as defined by the
# Peewee models to a format usable by Alembic.
target_metadata = gen_sqlalchemy_metadata(all_models, LEGACY_INDEX_MAP)
tables = AttrDict(target_metadata.tables)


def get_db_url():
    """
    Return the Database URI. This is typically set in config.yaml but may be overridden using
    an environment variable or expected to default with a SQLite database for testing purposes.
    """
    db_url = app.config.get("DB_URI", "sqlite:///test/data/test.db")
    db_url = unquote(db_url)  # TODO: determine and comment why this is important
    return db_url


def get_tester():
    """
    Returns the tester to use.

    We only return the tester that populates data if the TEST_MIGRATE env var is set to `true` AND
    we make sure we're not connecting to a production database.
    """
    db_url = get_db_url()
    if os.environ.get("TEST_MIGRATE", "") == "true":
        if db_url.find("amazonaws.com") < 0:
            return PopulateTestDataTester()

    return NoopTester()


def get_engine():
    """
    Return a SQL Alchemy engine object which Alembic uses to connect to the database.
    """
    db_url = get_db_url()
    peewee_connection_args = app.config.get("DB_CONNECTION_ARGS", {})
    sa_connection_args = {}

    # Include MySQL/MariaDB SSL configuration
    if "ssl" in peewee_connection_args:
        sa_connection_args["ssl"] = peewee_connection_args["ssl"]

    engine = create_engine(db_url, connect_args=sa_connection_args)
    return engine


def run_migrations_offline():
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    db_url = get_db_url()
    config.set_main_option("sqlalchemy.url", db_url)  # TODO: Is this required?
    context.configure(url=db_url, target_metadata=target_metadata, transactional_ddl=True)

    with context.begin_transaction():
        context.run_migrations(op=alembic_op, tables=tables, tester=get_tester())


def run_migrations_online():
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection with the context.
    """
    if isinstance(db.obj, SqliteDatabase) and "DB_URI" not in os.environ:
        logger.info("Skipping Sqlite migration!")
        return

    engine = get_engine()
    connection = engine.connect()
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        transactional_ddl=False,
    )

    try:
        with context.begin_transaction():
            try:
                context.run_migrations(op=alembic_op, tables=tables, tester=get_tester())
            except (CommandError, ResolutionError) as ex:
                if "No such revision" not in str(ex):
                    raise

                if not REGION or not GIT_HEAD:
                    raise

                from data.model.release import get_recent_releases

                # ignore revision error if we're running the previous release
                releases = list(get_recent_releases(SERVICE, REGION).offset(1).limit(1))
                if releases and releases[0].version == GIT_HEAD:
                    logger.warn("Skipping database migration because revision not found")
                else:
                    raise
    finally:
        connection.close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
