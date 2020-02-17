import logging

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.environment import EnvironmentContext
from alembic.migration import __name__ as migration_name


def run_alembic_migration(db_uri, log_handler=None, setup_app=True):
    if log_handler:
        logging.getLogger(migration_name).addHandler(log_handler)

    config = Config()
    config.set_main_option("script_location", "data:migrations")
    config.set_main_option("db_uri", db_uri)

    if setup_app:
        config.set_main_option("alembic_setup_app", "True")
    else:
        config.set_main_option("alembic_setup_app", "")

    script = ScriptDirectory.from_config(config)

    def fn(rev, context):
        return script._upgrade_revs("head", rev)

    with EnvironmentContext(config, script, fn=fn, destination_rev="head"):
        script.run_env()
