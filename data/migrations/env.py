import logging
import os

from logging.config import fileConfig
from functools import partial
from urllib.parse import unquote

from alembic import context, op as alembic_op
from alembic.script.revision import ResolutionError
from alembic.util import CommandError
from sqlalchemy import create_engine, engine_from_config, pool
from peewee import SqliteDatabase

from app import app
from data.database import all_models, db, LEGACY_INDEX_MAP
from data.migrations.tester import NoopTester, PopulateTestDataTester
from data.model.sqlalchemybridge import gen_sqlalchemy_metadata
from release import GIT_HEAD, REGION, SERVICE
from util.morecollections import AttrDict
from util.parsing import truthy_bool
from data.migrations.progress import PrometheusReporter, NullReporter, ProgressWrapper
from data.migrations.dba_operator import Migration, OpLogger


TEST_DB_URI = "sqlite:///test/data/test.db"
DB_URI = app.config.get("DB_URI", TEST_DB_URI) 
DB_CONNECTION_ARGS = app.config.get("DB_CONNECTION_ARGS")


config = context.config
PROM_LABEL_PREFIX = "DBA_OP_LABEL_"


config.set_main_option("sqlalchemy.url", unquote(DB_URI))
# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name:
    fileConfig(config.config_file_name)

logger = logging.getLogger(__name__)


# Model Metadata used for auto-generating new migrations.
# Traditionally, this would be the Metadata class for SQLAlchemy models. As Quay
# uses Peewee instead of SQLAlchemy, extra manipulation is required.
target_metadata = gen_sqlalchemy_metadata(all_models, LEGACY_INDEX_MAP)
tables = AttrDict(target_metadata.tables)



def get_tester():
    """
    Returns the tester to use.

    We only return the tester that populates data if the TEST_MIGRATE env var is set to `true` AND
    we make sure we're not connecting to a production database.
    """
    if os.environ.get("TEST_MIGRATE", "") == "true":
        url = unquote(DB_URI)
        if url.find("amazonaws.com") < 0:
            return PopulateTestDataTester()

    return NoopTester()


def get_progress_reporter():
    prom_addr = os.environ.get("DBA_OP_PROMETHEUS_PUSH_GATEWAY_ADDR", None)

    if prom_addr is not None:
        prom_job = os.environ.get("DBA_OP_JOB_ID")

        def _process_label_key(label_key):
            return label_key[len(PROM_LABEL_PREFIX) :].lower()

        labels = {
            _process_label_key(k): v
            for k, v in list(os.environ.items())
            if k.startswith(PROM_LABEL_PREFIX)
        }

        return PrometheusReporter(prom_addr, prom_job, labels)
    else:
        return NullReporter()


def report_success(ctx=None, step=None, heads=None, run_args=None):
    progress_reporter = ctx.config.attributes["progress_reporter"]
    progress_reporter.report_version_complete(success=True)


def finish_migration(migration, ctx=None, step=None, heads=None, run_args=None):
    write_dba_operator_migration(
        migration, step.up_revision.revision, step.up_revision.down_revision
    )


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
    url = unquote(DB_URI)
    context.configure(url=url, target_metadata=target_metadata, transactional_ddl=True)
    context.config.attributes["progress_reporter"] = progress_reporter
    op = ProgressWrapper(alembic_op, NullReporter())

    with context.begin_transaction():
        context.run_migrations(op=op, tables=tables, tester=get_tester())


def run_migrations_online():
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection with the context.
    """

    if isinstance(db.obj, SqliteDatabase) and not "DB_URI" in os.environ:
        print("Skipping Sqlite migration!")
        return

    progress_reporter = get_progress_reporter()
    context.config.attributes["progress_reporter"] = progress_reporter
    op = ProgressWrapper(alembic_op, progress_reporter)

    migration = Migration()
    version_apply_callback = report_success
    if truthy_bool(
        context.get_x_argument(as_dictionary=True).get("generatedbaopmigrations", False)
    ):
        op = OpLogger(alembic_op, migration)
        version_apply_callback = partial(finish_migration, migration)

    uri = unquote(DB_URI)

    # Threadlocals are no longer supported and were only used by Peewee.
    # Exclude from being used when creating the connection.
    if DB_CONNECTION_ARGS and "threadlocals" in DB_CONNECTION_ARGS:
        del DB_CONNECTION_ARGS["threadlocals"]

    # Autorollback is a Peewee feature. It is not an argument used by
    # the database drivers. Exclude it from being used when creating
    # a connection.
    if DB_CONNECTION_ARGS and "autorollback" in DB_CONNECTION_ARGS:
        del DB_CONNECTION_ARGS["autorollback"]

    engine = create_engine(uri, connect_args=DB_CONNECTION_ARGS)

    revision_to_migration = {}

    def process_revision_directives(context, revision, directives):
        script = directives[0]
        migration = Migration()
        revision_to_migration[(script.rev_id, revision)] = migration
        migration.add_hints_from_ops(script.upgrade_ops)

    connection = engine.connect()
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        transactional_ddl=False,
        on_version_apply=version_apply_callback,
        process_revision_directives=process_revision_directives,
    )

    try:
        with context.begin_transaction():
            try:
                context.run_migrations(op=op, tables=tables, tester=get_tester())
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

    for (revision, previous_revision), migration in revision_to_migration.items():
        write_dba_operator_migration(migration, revision, previous_revision)


def write_dba_operator_migration(migration, revision, previous_revision):
    migration_filename = "{}-databasemigration.yaml".format(revision)
    output_filename = os.path.join("data", "migrations", "dba_operator", migration_filename)
    with open(output_filename, "w") as migration_file:
        migration_file.write("\n---\n")
        migration.dump_yaml_and_reset(migration_file, revision, previous_revision)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
