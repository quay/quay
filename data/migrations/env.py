import logging
import os

from logging.config import fileConfig
from functools import partial
from urllib.parse import unquote

from alembic import context, op as alembic_op
from alembic.script.revision import ResolutionError
from alembic.util import CommandError
from sqlalchemy import engine_from_config, pool
from peewee import SqliteDatabase

from data.database import all_models, db, LEGACY_INDEX_MAP
from data.migrations.tester import NoopTester, PopulateTestDataTester
from data.model.sqlalchemybridge import gen_sqlalchemy_metadata
from release import GIT_HEAD, REGION, SERVICE
from util.morecollections import AttrDict
from util.parsing import truthy_bool
from data.migrations.progress import PrometheusReporter, NullReporter, ProgressWrapper
from data.migrations.dba_operator import Migration, OpLogger


config = context.config
DB_URI = config.get_main_option("db_uri", "sqlite:///test/data/test.db")
PROM_LABEL_PREFIX = "DBA_OP_LABEL_"

# This option exists because alembic needs the db proxy to be configured in order
# to perform migrations. The app import does the init of the proxy, but we don't
# want that in the case of the config app, as we are explicitly connecting to a
# db that the user has passed in, and we can't have import dependency on app
if config.get_main_option("alembic_setup_app", "True") == "True":
    from app import app

    DB_URI = app.config["DB_URI"]

config.set_main_option("sqlalchemy.url", unquote(DB_URI))
# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name:
    fileConfig(config.config_file_name)

logger = logging.getLogger(__name__)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = gen_sqlalchemy_metadata(all_models, LEGACY_INDEX_MAP)
tables = AttrDict(target_metadata.tables)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


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

    engine = engine_from_config(
        config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool
    )

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
