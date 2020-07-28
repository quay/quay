import os

from cachetools.func import lru_cache
from collections import namedtuple
from datetime import datetime, timedelta

import pytest
import shutil
import inspect

from flask import Flask, jsonify
from flask_login import LoginManager
from flask_principal import identity_loaded, Permission, Identity, identity_changed, Principal
from flask_mail import Mail
from peewee import SqliteDatabase, InternalError
from mock import patch

from app import app as application
from auth.permissions import on_identity_loaded
from data import model
from data.database import close_db_filter, db, configure
from data.model.user import LoginWrappedDBUser, create_robot, lookup_robot, create_user_noverify
from data.userfiles import Userfiles
from endpoints.api import api_bp
from endpoints.appr import appr_bp
from endpoints.web import web
from endpoints.v1 import v1_bp
from endpoints.v2 import v2_bp
from endpoints.webhooks import webhooks

from initdb import initialize_database, populate_database

from path_converters import APIRepositoryPathConverter, RegexConverter, RepositoryPathConverter
from test.testconfig import FakeTransaction

INIT_DB_PATH = 0


@pytest.fixture(scope="session")
def init_db_path(tmpdir_factory):
    """
    Creates a new database and appropriate configuration.

    Note that the initial database is created *once* per session. In the non-full-db-test case, the
    database_uri fixture makes a copy of the SQLite database file on disk and passes a new copy to
    each test.
    """
    # NOTE: We use a global here because pytest runs this code multiple times, due to the fixture
    # being imported instead of being in a conftest. Moving to conftest has its own issues, and this
    # call is quite slow, so we simply cache it here.
    global INIT_DB_PATH
    INIT_DB_PATH = INIT_DB_PATH or _init_db_path(tmpdir_factory)
    return INIT_DB_PATH


def _init_db_path(tmpdir_factory):
    if os.environ.get("TEST_DATABASE_URI"):
        return _init_db_path_real_db(os.environ.get("TEST_DATABASE_URI"))

    return _init_db_path_sqlite(tmpdir_factory)


def _init_db_path_real_db(db_uri):
    """
    Initializes a real database for testing by populating it from scratch. Note that this does.

    *not* add the tables (merely data). Callers must have migrated the database before calling
    the test suite.
    """
    configure(
        {
            "DB_URI": db_uri,
            "SECRET_KEY": "superdupersecret!!!1",
            "DB_CONNECTION_ARGS": {"threadlocals": True, "autorollback": True,},
            "DB_TRANSACTION_FACTORY": _create_transaction,
            "DATABASE_SECRET_KEY": "anothercrazykey!",
        }
    )

    populate_database()
    return db_uri


def _init_db_path_sqlite(tmpdir_factory):
    """
    Initializes a SQLite database for testing by populating it from scratch and placing it into a
    temp directory file.
    """
    sqlitedbfile = str(tmpdir_factory.mktemp("data").join("test.db"))
    sqlitedb = "sqlite:///{0}".format(sqlitedbfile)
    conf = {
        "TESTING": True,
        "DEBUG": True,
        "SECRET_KEY": "superdupersecret!!!1",
        "DATABASE_SECRET_KEY": "anothercrazykey!",
        "DB_URI": sqlitedb,
    }
    os.environ["DB_URI"] = str(sqlitedb)
    db.initialize(SqliteDatabase(sqlitedbfile))
    application.config.update(conf)
    application.config.update({"DB_URI": sqlitedb})
    initialize_database()

    db.obj.execute_sql("PRAGMA foreign_keys = ON;")
    db.obj.execute_sql('PRAGMA encoding="UTF-8";')

    populate_database()
    close_db_filter(None)
    return str(sqlitedbfile)


@pytest.yield_fixture()
def database_uri(monkeypatch, init_db_path, sqlitedb_file):
    """
    Returns the database URI to use for testing.

    In the SQLite case, a new, distinct copy of the SQLite database is created by copying the
    initialized database file (sqlitedb_file) on a per-test basis. In the non-SQLite case, a
    reference to the existing database URI is returned.
    """
    if os.environ.get("TEST_DATABASE_URI"):
        db_uri = os.environ["TEST_DATABASE_URI"]
        monkeypatch.setenv("DB_URI", db_uri)
        yield db_uri
    else:
        # Copy the golden database file to a new path.
        shutil.copy2(init_db_path, sqlitedb_file)

        # Monkeypatch the DB_URI.
        db_path = "sqlite:///{0}".format(sqlitedb_file)
        monkeypatch.setenv("DB_URI", db_path)
        yield db_path

        # Delete the DB copy.
        assert ".." not in sqlitedb_file
        assert "test.db" in sqlitedb_file
        os.remove(sqlitedb_file)


@pytest.fixture()
def sqlitedb_file(tmpdir):
    """
    Returns the path at which the initialized, golden SQLite database file will be placed.
    """
    test_db_file = tmpdir.mkdir("quaydb").join("test.db")
    return str(test_db_file)


def _create_transaction(db):
    return FakeTransaction()


@pytest.fixture()
def appconfig(database_uri):
    """
    Returns application configuration for testing that references the proper database URI.
    """
    conf = {
        "TESTING": True,
        "DEBUG": True,
        "DB_URI": database_uri,
        "SECRET_KEY": "superdupersecret!!!1",
        "DATABASE_SECRET_KEY": "anothercrazykey!",
        "DB_CONNECTION_ARGS": {"threadlocals": True, "autorollback": True,},
        "DB_TRANSACTION_FACTORY": _create_transaction,
        "DATA_MODEL_CACHE_CONFIG": {"engine": "inmemory",},
        "USERFILES_PATH": "userfiles/",
        "MAIL_SERVER": "",
        "MAIL_DEFAULT_SENDER": "support@quay.io",
        "DATABASE_SECRET_KEY": "anothercrazykey!",
    }
    return conf


AllowedAutoJoin = namedtuple("AllowedAutoJoin", ["frame_start_index", "pattern_prefixes"])


ALLOWED_AUTO_JOINS = [
    AllowedAutoJoin(0, ["test_"]),
    AllowedAutoJoin(0, ["<", "test_"]),
]

CALLER_FRAMES_OFFSET = 3
FRAME_NAME_INDEX = 3


@pytest.fixture()
def initialized_db(appconfig):
    """
    Configures the database for the database found in the appconfig.
    """
    under_test_real_database = bool(os.environ.get("TEST_DATABASE_URI"))

    # Configure the database.
    configure(appconfig)

    # Initialize caches.
    model._basequery._lookup_team_roles()
    model._basequery.get_public_repo_visibility()
    model.log.get_log_entry_kinds()

    if not under_test_real_database:
        # Make absolutely sure foreign key constraints are on.
        db.obj.execute_sql("PRAGMA foreign_keys = ON;")
        db.obj.execute_sql('PRAGMA encoding="UTF-8";')
        assert db.obj.execute_sql("PRAGMA foreign_keys;").fetchone()[0] == 1
        assert db.obj.execute_sql("PRAGMA encoding;").fetchone()[0] == "UTF-8"

    # If under a test *real* database, setup a savepoint.
    if under_test_real_database:
        with db.transaction():
            test_savepoint = db.savepoint()
            test_savepoint.__enter__()

            yield  # Run the test.

            try:
                test_savepoint.rollback()
                test_savepoint.__exit__(None, None, None)
            except InternalError:
                # If postgres fails with an exception (like IntegrityError) mid-transaction, it terminates
                # it immediately, so when we go to remove the savepoint, it complains. We can safely ignore
                # this case.
                pass
    else:
        if os.environ.get("DISALLOW_AUTO_JOINS", "false").lower() == "true":
            # Patch get_rel_instance to fail if we try to load any non-joined foreign key. This will allow
            # us to catch missing joins when running tests.
            def get_rel_instance(self, instance):
                value = instance.__data__.get(self.name)
                if value is not None or self.name in instance.__rel__:
                    if self.name not in instance.__rel__:
                        # NOTE: We only raise an exception if this auto-lookup occurs from non-testing code.
                        # Testing code can be a bit inefficient.
                        lookup_allowed = False

                        try:
                            outerframes = inspect.getouterframes(inspect.currentframe())
                        except IndexError:
                            # Happens due to a bug in Jinja.
                            outerframes = []

                        for allowed_auto_join in ALLOWED_AUTO_JOINS:
                            if lookup_allowed:
                                break

                            if (
                                len(outerframes)
                                >= allowed_auto_join.frame_start_index + CALLER_FRAMES_OFFSET
                            ):
                                found_match = True
                                for index, pattern_prefix in enumerate(
                                    allowed_auto_join.pattern_prefixes
                                ):
                                    frame_info = outerframes[index + CALLER_FRAMES_OFFSET]
                                    if not frame_info[FRAME_NAME_INDEX].startswith(pattern_prefix):
                                        found_match = False
                                        break

                                if found_match:
                                    lookup_allowed = True
                                    break

                        if not lookup_allowed:
                            raise Exception(
                                "Missing join on instance `%s` for field `%s`", instance, self.name
                            )

                        obj = self.rel_model.get(self.field.rel_field == value)
                        instance.__rel__[self.name] = obj
                    return instance.__rel__[self.name]
                elif not self.field.null:
                    raise self.rel_model.DoesNotExist

                return value

            with patch("peewee.ForeignKeyAccessor.get_rel_instance", get_rel_instance):
                yield
        else:
            yield


@pytest.fixture()
def app(appconfig, initialized_db):
    """
    Used by pytest-flask plugin to inject a custom app instance for testing.
    """
    app = Flask(__name__)
    login_manager = LoginManager(app)

    @app.errorhandler(model.DataModelException)
    def handle_dme(ex):
        response = jsonify({"message": str(ex)})
        response.status_code = 400
        return response

    @login_manager.user_loader
    def load_user(user_uuid):
        return LoginWrappedDBUser(user_uuid)

    @identity_loaded.connect_via(app)
    def on_identity_loaded_for_test(sender, identity):
        on_identity_loaded(sender, identity)

    Principal(app, use_sessions=False)

    app.url_map.converters["regex"] = RegexConverter
    app.url_map.converters["apirepopath"] = APIRepositoryPathConverter
    app.url_map.converters["repopath"] = RepositoryPathConverter

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(appr_bp, url_prefix="/cnr")
    app.register_blueprint(web, url_prefix="/")
    app.register_blueprint(v1_bp, url_prefix="/v1")
    app.register_blueprint(v2_bp, url_prefix="/v2")
    app.register_blueprint(webhooks, url_prefix="/webhooks")

    app.config.update(appconfig)

    Userfiles(app)
    Mail(app)

    return app
