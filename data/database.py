# pylint: disable=old-style-class,no-init

import inspect
import logging
import string
import sys
import time
import uuid
import os

from contextlib import contextmanager
from collections import defaultdict, namedtuple
from datetime import datetime
from random import SystemRandom

import toposort

from enum import IntEnum, Enum, unique
from peewee import *
from peewee import __exception_wrapper__, Function
from playhouse.pool import PooledMySQLDatabase, PooledPostgresqlDatabase, PooledSqliteDatabase

from sqlalchemy.engine.url import make_url

import rehash
from cachetools.func import lru_cache

from data.fields import (
    ResumableSHA256Field,
    ResumableSHA1Field,
    JSONField,
    Base64BinaryField,
    FullIndexedTextField,
    FullIndexedCharField,
    EnumField as ClientEnumField,
    EncryptedTextField,
    EncryptedCharField,
    CredentialField,
)
from data.decorators import deprecated_model
from data.text import match_mysql, match_like
from data.encryption import FieldEncrypter
from data.readreplica import ReadReplicaSupportedModel, ReadOnlyConfig, disallow_replica_use
from data.estimate import mysql_estimate_row_count, normal_row_count
from util.names import urn_generator
from util.validation import validate_postgres_precondition


logger = logging.getLogger(__name__)

DEFAULT_DB_CONNECT_TIMEOUT = 10  # seconds


# IMAGE_NOT_SCANNED_ENGINE_VERSION is the version found in security_indexed_engine when the
# image has not yet been scanned.
IMAGE_NOT_SCANNED_ENGINE_VERSION = -1

schemedriver = namedtuple("schemedriver", ["driver", "pooled_driver"])

_SCHEME_DRIVERS = {
    "mysql": schemedriver(MySQLDatabase, PooledMySQLDatabase),
    "mysql+pymysql": schemedriver(MySQLDatabase, PooledMySQLDatabase),
    "sqlite": schemedriver(SqliteDatabase, PooledSqliteDatabase),
    "postgresql": schemedriver(PostgresqlDatabase, PooledPostgresqlDatabase),
    "postgresql+psycopg2": schemedriver(PostgresqlDatabase, PooledPostgresqlDatabase),
}


SCHEME_MATCH_FUNCTION = {
    "mysql": match_mysql,
    "mysql+pymysql": match_mysql,
    "sqlite": match_like,
    "postgresql": match_like,
    "postgresql+psycopg2": match_like,
}


SCHEME_RANDOM_FUNCTION = {
    "mysql": fn.Rand,
    "mysql+pymysql": fn.Rand,
    "sqlite": fn.Random,
    "postgresql": fn.Random,
    "postgresql+psycopg2": fn.Random,
}


SCHEME_ESTIMATOR_FUNCTION = {
    "mysql": mysql_estimate_row_count,
    "mysql+pymysql": mysql_estimate_row_count,
    "sqlite": normal_row_count,
    "postgresql": normal_row_count,
    "postgresql+psycopg2": normal_row_count,
}


PRECONDITION_VALIDATION = {
    "postgresql": validate_postgres_precondition,
    "postgresql+psycopg2": validate_postgres_precondition,
}


_EXTRA_ARGS = {
    "mysql": dict(charset="utf8mb4"),
    "mysql+pymysql": dict(charset="utf8mb4"),
}


def pipes_concat(arg1, arg2, *extra_args):
    """
    Concat function for sqlite, since it doesn't support fn.Concat.

    Concatenates clauses with || characters.
    """
    reduced = arg1.concat(arg2)
    for arg in extra_args:
        reduced = reduced.concat(arg)
    return reduced


def function_concat(arg1, arg2, *extra_args):
    """
    Default implementation of concat which uses fn.Concat().

    Used by all database engines except sqlite.
    """
    return fn.Concat(arg1, arg2, *extra_args)


SCHEME_SPECIALIZED_CONCAT = {
    "sqlite": pipes_concat,
}


def real_for_update(query):
    return query.for_update()


def null_for_update(query):
    return query


def delete_instance_filtered(instance, model_class, delete_nullable, skip_transitive_deletes):
    """
    Deletes the DB instance recursively, skipping any models in the skip_transitive_deletes set.

    Callers *must* ensure that any models listed in the skip_transitive_deletes must be capable
    of being directly deleted when the instance is deleted (with automatic sorting handling
    dependency order) - for example, the Manifest and ManifestBlob tables for Repository will
    always refer to the *same* repository when Manifest references ManifestBlob, so we can safely
    skip transitive deletion for the Manifest table.

    Callers *must* catch IntegrityError's raised, as this method will *not* delete the instance
    under a transaction, to avoid locking the database.
    """
    # We need to sort the ops so that models get cleaned in order of their dependencies
    ops = reversed(list(instance.dependencies(delete_nullable)))
    filtered_ops = []

    dependencies = defaultdict(set)

    for query, fk in ops:
        # We only want to skip transitive deletes, which are done using subqueries in the form of
        # DELETE FROM <table> in <subquery>. If an op is not using a subquery, we allow it to be
        # applied directly.
        if fk.model not in skip_transitive_deletes or query.op.lower() != "in":
            filtered_ops.append((query, fk))

        if query.op.lower() == "in":
            dependencies[fk.model.__name__].add(query.rhs.model.__name__)
        elif query.op == "=":
            dependencies[fk.model.__name__].add(model_class.__name__)
        else:
            raise RuntimeError("Unknown operator in recursive repository delete query")

    sorted_models = list(reversed(toposort.toposort_flatten(dependencies)))

    def sorted_model_key(query_fk_tuple):
        cmp_query, cmp_fk = query_fk_tuple
        if cmp_query.op.lower() == "in":
            return -1
        return sorted_models.index(cmp_fk.model.__name__)

    filtered_ops.sort(key=sorted_model_key)

    # NOTE: We do not use a transaction here, as it can be a VERY long transaction, potentially
    # locking up the database. Instead, we expect cleanup code to have run before this point, and
    # if this fails with an IntegrityError, callers are expected to catch and retry.
    for query, fk in filtered_ops:
        _model = fk.model
        if fk.null and not delete_nullable:
            _model.update(**{fk.name: None}).where(query).execute()
        else:
            _model.delete().where(query).execute()

    return instance.delete().where(instance._pk_expr()).execute()


SCHEME_SPECIALIZED_FOR_UPDATE = {
    "sqlite": null_for_update,
}


class CallableProxy(Proxy):
    def __call__(self, *args, **kwargs):
        if self.obj is None:
            raise AttributeError("Cannot use uninitialized Proxy.")
        return self.obj(*args, **kwargs)


class RetryOperationalError(object):
    def execute_sql(self, sql, params=None, commit=True):
        try:
            cursor = super(RetryOperationalError, self).execute_sql(sql, params, commit)
        except OperationalError:
            if not self.is_closed():
                self.close()

            with __exception_wrapper__:
                cursor = self.cursor()
                cursor.execute(sql, params or ())
                if commit and not self.in_transaction():
                    self.commit()

        return cursor


class CloseForLongOperation(object):
    """
    Helper object which disconnects the database then reconnects after the nested operation
    completes.
    """

    def __init__(self, config_object):
        self.config_object = config_object

    def __enter__(self):
        if self.config_object.get("TESTING") is True:
            return

        close_db_filter(None)

    def __exit__(self, typ, value, traceback):
        # Note: Nothing to do. The next SQL call will reconnect automatically.
        pass


class UseThenDisconnect(object):
    """
    Helper object for conducting work with a database and then tearing it down.
    """

    def __init__(self, config_object):
        self.config_object = config_object

    def __enter__(self):
        pass

    def __exit__(self, typ, value, traceback):
        if self.config_object.get("TESTING") is True:
            return

        close_db_filter(None)


class TupleSelector(object):
    """
    Helper class for selecting tuples from a peewee query and easily accessing them as if they were
    objects.
    """

    class _TupleWrapper(object):
        def __init__(self, data, fields):
            self._data = data
            self._fields = fields

        def get(self, field):
            return self._data[self._fields.index(TupleSelector.tuple_reference_key(field))]

    @classmethod
    def tuple_reference_key(cls, field):
        """
        Returns a string key for referencing a field in a TupleSelector.
        """
        if isinstance(field, Function):
            return field.name + ",".join([cls.tuple_reference_key(arg) for arg in field.arguments])

        if isinstance(field, Field):
            return field.name + ":" + field.model.__name__

        raise Exception("Unknown field type %s in TupleSelector" % field._node_type)

    def __init__(self, query, fields):
        self._query = query.select(*fields).tuples()
        self._fields = [TupleSelector.tuple_reference_key(field) for field in fields]

    def __iter__(self):
        return self._build_iterator()

    def _build_iterator(self):
        for tuple_data in self._query:
            yield TupleSelector._TupleWrapper(tuple_data, self._fields)


db = Proxy()
read_only_config = Proxy()
db_random_func = CallableProxy()
db_match_func = CallableProxy()
db_for_update = CallableProxy()
db_transaction = CallableProxy()
db_disallow_replica_use = CallableProxy()
db_concat_func = CallableProxy()
db_encrypter = Proxy()
db_count_estimator = CallableProxy()
ensure_under_transaction = CallableProxy()


def validate_database_url(url, db_kwargs, connect_timeout=5):
    """
    Validates that we can connect to the given database URL, with the given kwargs.

    Raises an exception if the validation fails.
    """
    db_kwargs = db_kwargs.copy()

    try:
        driver = _db_from_url(
            url, db_kwargs, connect_timeout=connect_timeout, allow_retry=False, allow_pooling=False
        )
        driver.connect()
    finally:
        try:
            driver.close()
        except:
            pass


def validate_database_precondition(url, db_kwargs, connect_timeout=5):
    """
    Validates that we can connect to the given database URL and the database meets our precondition.

    Raises an exception if the validation fails.
    """
    db_kwargs = db_kwargs.copy()
    try:
        driver = _db_from_url(
            url, db_kwargs, connect_timeout=connect_timeout, allow_retry=False, allow_pooling=False
        )
        driver.connect()
        pre_condition_check = PRECONDITION_VALIDATION.get(make_url(url).drivername)
        if pre_condition_check:
            pre_condition_check(driver)

    finally:
        try:
            driver.close()
        except:
            pass


def _wrap_for_retry(driver):
    return type("Retrying" + driver.__name__, (RetryOperationalError, driver), {})


def _db_from_url(
    url,
    db_kwargs,
    connect_timeout=DEFAULT_DB_CONNECT_TIMEOUT,
    allow_pooling=True,
    allow_retry=True,
    is_read_replica=False,
):
    parsed_url = make_url(url)

    if parsed_url.host:
        db_kwargs["host"] = parsed_url.host
    if parsed_url.port:
        db_kwargs["port"] = parsed_url.port
    if parsed_url.username:
        db_kwargs["user"] = parsed_url.username
    if parsed_url.password:
        db_kwargs["password"] = parsed_url.password

    # Remove threadlocals. It used to be required.
    db_kwargs.pop("threadlocals", None)

    # Note: sqlite does not support connect_timeout.
    if parsed_url.drivername != "sqlite":
        db_kwargs["connect_timeout"] = db_kwargs.get("connect_timeout", connect_timeout)

    drivers = _SCHEME_DRIVERS[parsed_url.drivername]
    driver = drivers.driver
    if allow_pooling and os.getenv("DB_CONNECTION_POOLING", "false").lower() == "true":
        driver = drivers.pooled_driver
        db_kwargs["stale_timeout"] = db_kwargs.get("stale_timeout", None)
        db_kwargs["max_connections"] = db_kwargs.get("max_connections", None)
        logger.info(
            "Connection pooling enabled for %s; stale timeout: %s; max connection count: %s",
            parsed_url.drivername,
            db_kwargs["stale_timeout"],
            db_kwargs["max_connections"],
        )
    else:
        logger.info("Connection pooling disabled for %s", parsed_url.drivername)
        db_kwargs.pop("stale_timeout", None)
        db_kwargs.pop("timeout", None)
        db_kwargs.pop("max_connections", None)

    for key, value in _EXTRA_ARGS.get(parsed_url.drivername, {}).items():
        if key not in db_kwargs:
            db_kwargs[key] = value

    if allow_retry:
        driver = _wrap_for_retry(driver)

    driver_autocommit = False
    if db_kwargs.get("_driver_autocommit"):
        assert is_read_replica, "_driver_autocommit can only be set for a read replica"
        driver_autocommit = db_kwargs["_driver_autocommit"]
        db_kwargs.pop("_driver_autocommit", None)

    created = driver(parsed_url.database, **db_kwargs)
    if driver_autocommit:
        created.connect_params["autocommit"] = driver_autocommit

    # Revert the behavior "fixed" in:
    # https://github.com/coleifer/peewee/commit/36bd887ac07647c60dfebe610b34efabec675706
    if parsed_url.drivername.find("mysql") >= 0:
        created.compound_select_parentheses = 0
    return created


def configure(config_object, testing=False):
    logger.debug("Configuring database")
    db_kwargs = dict(config_object["DB_CONNECTION_ARGS"])
    write_db_uri = config_object["DB_URI"]
    db.initialize(_db_from_url(write_db_uri, db_kwargs))

    parsed_write_uri = make_url(write_db_uri)
    db_random_func.initialize(SCHEME_RANDOM_FUNCTION[parsed_write_uri.drivername])
    db_match_func.initialize(SCHEME_MATCH_FUNCTION[parsed_write_uri.drivername])
    db_for_update.initialize(
        SCHEME_SPECIALIZED_FOR_UPDATE.get(parsed_write_uri.drivername, real_for_update)
    )
    db_concat_func.initialize(
        SCHEME_SPECIALIZED_CONCAT.get(parsed_write_uri.drivername, function_concat)
    )
    db_encrypter.initialize(FieldEncrypter(config_object.get("DATABASE_SECRET_KEY")))
    db_count_estimator.initialize(SCHEME_ESTIMATOR_FUNCTION[parsed_write_uri.drivername])

    read_replicas = config_object.get("DB_READ_REPLICAS", None)
    is_read_only = config_object.get("REGISTRY_STATE", "normal") == "readonly"

    read_replica_dbs = []
    if read_replicas:
        read_replica_dbs = [
            _db_from_url(
                ro_config["DB_URI"],
                ro_config.get("DB_CONNECTION_ARGS", db_kwargs),
                is_read_replica=True,
            )
            for ro_config in read_replicas
        ]

    read_only_config.initialize(ReadOnlyConfig(is_read_only, read_replica_dbs))

    def _db_transaction():
        return config_object["DB_TRANSACTION_FACTORY"](db)

    def _db_disallow_replica_use():
        return disallow_replica_use(db)

    @contextmanager
    def _ensure_under_transaction():
        if not testing and not config_object["TESTING"]:
            if db.transaction_depth() == 0:
                raise Exception("Expected to be under a transaction")

        yield

    db_transaction.initialize(_db_transaction)
    db_disallow_replica_use.initialize(_db_disallow_replica_use)
    ensure_under_transaction.initialize(_ensure_under_transaction)


def random_string_generator(length=16):
    def random_string():
        random = SystemRandom()
        return "".join(
            [random.choice(string.ascii_uppercase + string.digits) for _ in range(length)]
        )

    return random_string


def uuid_generator():
    return str(uuid.uuid4())


get_epoch_timestamp = lambda: int(time.time())
get_epoch_timestamp_ms = lambda: int(time.time() * 1000)


def close_db_filter(_):
    if db.obj is not None and not db.is_closed():
        logger.debug("Disconnecting from database.")
        db.close()

    if read_only_config.obj is not None:
        for read_replica in read_only_config.obj.read_replicas:
            if not read_replica.is_closed():
                logger.debug("Disconnecting from read replica.")
                read_replica.close()


class QuayUserField(ForeignKeyField):
    def __init__(self, allows_robots=False, robot_null_delete=False, *args, **kwargs):
        self.allows_robots = allows_robots
        self.robot_null_delete = robot_null_delete
        if "model" not in kwargs:
            kwargs["model"] = User
        super(QuayUserField, self).__init__(*args, **kwargs)


@lru_cache(maxsize=16)
def _get_enum_field_values(enum_field):
    values = []
    for row in enum_field.rel_model.select():
        key = getattr(row, enum_field.enum_key_field)
        value = getattr(row, "id")
        values.append((key, value))
    return Enum(enum_field.rel_model.__name__, values)


class EnumField(ForeignKeyField):
    """
    Create a cached python Enum from an EnumTable.
    """

    def __init__(self, model, enum_key_field="name", *args, **kwargs):
        """
        model is the EnumTable model-class (see ForeignKeyField) enum_key_field is the field from
        the EnumTable to use as the enum name.
        """
        self.enum_key_field = enum_key_field
        super(EnumField, self).__init__(model, *args, **kwargs)

    @property
    def enum(self):
        """
        Returns a python enun.Enum generated from the associated EnumTable.
        """
        return _get_enum_field_values(self)

    def get_id(self, name):
        """Returns the ForeignKeyId from the name field
        Example:
           >>> Repository.repo_kind.get_id("application")
           2
        """
        try:
            return self.enum[name].value
        except KeyError:
            raise self.rel_model.DoesNotExist

    def get_name(self, value):
        """Returns the name value from the ForeignKeyId
        Example:
           >>> Repository.repo_kind.get_name(2)
           "application"
        """
        try:
            return self.enum(value).name
        except ValueError:
            raise self.rel_model.DoesNotExist


def deprecated_field(field, flag):
    """
    Marks a field as deprecated and removes it from the peewee model if the flag is not set.

    A flag is defined in the active_migration module and will be associated with one or more
    migration phases.
    """
    if ActiveDataMigration.has_flag(flag):
        return field

    return None


class BaseModel(ReadReplicaSupportedModel):
    class Meta:
        database = db
        encrypter = db_encrypter
        read_only_config = read_only_config

    def __getattribute__(self, name):
        """
        Adds _id accessors so that foreign key field IDs can be looked up without making a database
        roundtrip.
        """
        if name.endswith("_id"):
            field_name = name[0 : len(name) - 3]
            if field_name in self._meta.fields:
                return self.__data__.get(field_name)

        return super(BaseModel, self).__getattribute__(name)


class User(BaseModel):
    uuid = CharField(default=uuid_generator, max_length=36, null=True, index=True)
    username = CharField(unique=True, index=True)
    password_hash = CharField(null=True)
    email = CharField(unique=True, index=True, default=random_string_generator(length=64))
    verified = BooleanField(default=False)
    stripe_id = CharField(index=True, null=True)
    organization = BooleanField(default=False, index=True)
    robot = BooleanField(default=False, index=True)
    invoice_email = BooleanField(default=False)
    invalid_login_attempts = IntegerField(default=0)
    last_invalid_login = DateTimeField(default=datetime.utcnow)
    removed_tag_expiration_s = IntegerField(default=1209600)  # Two weeks
    enabled = BooleanField(default=True)
    invoice_email_address = CharField(null=True, index=True)

    given_name = CharField(null=True)
    family_name = CharField(null=True)
    company = CharField(null=True)
    location = CharField(null=True)

    maximum_queued_builds_count = IntegerField(null=True)
    creation_date = DateTimeField(default=datetime.utcnow, null=True)
    last_accessed = DateTimeField(null=True, index=True)

    def delete_instance(self, recursive=False, delete_nullable=False):
        # If we are deleting a robot account, only execute the subset of queries necessary.
        if self.robot:
            # For all the model dependencies, only delete those that allow robots.
            for query, fk in reversed(list(self.dependencies(search_nullable=True))):
                if isinstance(fk, QuayUserField) and fk.allows_robots:
                    _model = fk.model

                    if fk.robot_null_delete:
                        _model.update(**{fk.name: None}).where(query).execute()
                    else:
                        _model.delete().where(query).execute()

            # Delete the instance itself.
            super(User, self).delete_instance(recursive=False, delete_nullable=False)
        else:
            if not recursive:
                raise RuntimeError("Non-recursive delete on user.")

            # These models don't need to use transitive deletes, because the referenced objects
            # are cleaned up directly in the model.
            skip_transitive_deletes = (
                {
                    Image,
                    Repository,
                    Team,
                    RepositoryBuild,
                    ServiceKeyApproval,
                    RepositoryBuildTrigger,
                    ServiceKey,
                    RepositoryPermission,
                    TeamMemberInvite,
                    Star,
                    RepositoryAuthorizedEmail,
                    TeamMember,
                    RepositoryTag,
                    PermissionPrototype,
                    DerivedStorageForImage,
                    TagManifest,
                    AccessToken,
                    OAuthAccessToken,
                    BlobUpload,
                    RepositoryNotification,
                    OAuthAuthorizationCode,
                    RepositoryActionCount,
                    TagManifestLabel,
                    TeamSync,
                    RepositorySearchScore,
                    DeletedNamespace,
                    DeletedRepository,
                    RepoMirrorRule,
                    NamespaceGeoRestriction,
                    ManifestSecurityStatus,
                    RepoMirrorConfig,
                    UploadedBlob,
                }
                | appr_classes
                | v22_classes
                | transition_classes
            )
            delete_instance_filtered(self, User, delete_nullable, skip_transitive_deletes)


Namespace = User.alias()


class RobotAccountMetadata(BaseModel):
    robot_account = QuayUserField(index=True, allows_robots=True, unique=True)
    description = CharField()
    unstructured_json = JSONField()


class RobotAccountToken(BaseModel):
    robot_account = QuayUserField(index=True, allows_robots=True, unique=True)
    token = EncryptedCharField(default_token_length=64)
    fully_migrated = BooleanField(default=False)


class DeletedNamespace(BaseModel):
    namespace = QuayUserField(index=True, allows_robots=False, unique=True)
    marked = DateTimeField(default=datetime.now)
    original_username = CharField(index=True)
    original_email = CharField(index=True)
    queue_id = CharField(null=True, index=True)


class NamespaceGeoRestriction(BaseModel):
    namespace = QuayUserField(index=True, allows_robots=False)
    added = DateTimeField(default=datetime.utcnow)
    description = CharField()
    unstructured_json = JSONField()
    restricted_region_iso_code = CharField(index=True)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = ((("namespace", "restricted_region_iso_code"), True),)


class UserPromptTypes(object):
    CONFIRM_USERNAME = "confirm_username"
    ENTER_NAME = "enter_name"
    ENTER_COMPANY = "enter_company"


class UserPromptKind(BaseModel):
    name = CharField(index=True)


class UserPrompt(BaseModel):
    user = QuayUserField(allows_robots=False, index=True)
    kind = ForeignKeyField(UserPromptKind)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = ((("user", "kind"), True),)


class TeamRole(BaseModel):
    name = CharField(index=True)


class Team(BaseModel):
    name = CharField(index=True)
    organization = QuayUserField(index=True)
    role = EnumField(TeamRole)
    description = TextField(default="")

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            # A team name must be unique within an organization
            (("name", "organization"), True),
        )


class TeamMember(BaseModel):
    user = QuayUserField(allows_robots=True, index=True)
    team = ForeignKeyField(Team)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            # A user may belong to a team only once
            (("user", "team"), True),
        )


class TeamMemberInvite(BaseModel):
    # Note: Either user OR email will be filled in, but not both.
    user = QuayUserField(index=True, null=True)
    email = CharField(null=True)
    team = ForeignKeyField(Team)
    inviter = ForeignKeyField(User, backref="inviter")
    invite_token = CharField(default=urn_generator(["teaminvite"]))


class LoginService(BaseModel):
    name = CharField(unique=True, index=True)


class TeamSync(BaseModel):
    team = ForeignKeyField(Team, unique=True)

    transaction_id = CharField()
    last_updated = DateTimeField(null=True, index=True)
    service = ForeignKeyField(LoginService)
    config = JSONField()


class FederatedLogin(BaseModel):
    user = QuayUserField(allows_robots=True, index=True)
    service = ForeignKeyField(LoginService)
    service_ident = CharField()
    metadata_json = TextField(default="{}")

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            # create a unique index on service and the local service id
            (("service", "service_ident"), True),
            # a user may only have one federated login per service
            (("service", "user"), True),
        )


class Visibility(BaseModel):
    name = CharField(index=True, unique=True)


class RepositoryKind(BaseModel):
    name = CharField(index=True, unique=True)


@unique
class RepositoryState(IntEnum):
    """
    Possible states of a repository.

    NORMAL:    Regular repo where all actions are possible
    READ_ONLY: Only read actions, such as pull, are allowed regardless of specific user permissions
    MIRROR:    Equivalent to READ_ONLY except that mirror robot has write permission
    MARKED_FOR_DELETION: Indicates the repository has been marked for deletion and should be hidden
                         and un-usable.
    """

    NORMAL = 0
    READ_ONLY = 1
    MIRROR = 2
    MARKED_FOR_DELETION = 3


class Repository(BaseModel):
    namespace_user = QuayUserField(null=True)
    name = FullIndexedCharField(match_function=db_match_func)
    visibility = EnumField(Visibility)
    description = FullIndexedTextField(match_function=db_match_func, null=True)
    badge_token = CharField(default=uuid_generator)
    kind = EnumField(RepositoryKind)
    trust_enabled = BooleanField(default=False)
    state = ClientEnumField(RepositoryState, default=RepositoryState.NORMAL)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            # create a unique index on namespace and name
            (("namespace_user", "name"), True),
        )

    def delete_instance(self, recursive=False, delete_nullable=False, force=False):
        if not recursive:
            raise RuntimeError("Non-recursive delete on repository.")

        assert force or self.state == RepositoryState.MARKED_FOR_DELETION

        # These models don't need to use transitive deletes, because the referenced objects
        # are cleaned up directly
        skip_transitive_deletes = (
            {
                RepositoryTag,
                RepositoryBuild,
                RepositoryBuildTrigger,
                BlobUpload,
                Image,
                TagManifest,
                TagManifestLabel,
                Label,
                DerivedStorageForImage,
                RepositorySearchScore,
                RepoMirrorConfig,
                RepoMirrorRule,
                DeletedRepository,
                ManifestSecurityStatus,
                UploadedBlob,
            }
            | appr_classes
            | v22_classes
            | transition_classes
        )

        delete_instance_filtered(self, Repository, delete_nullable, skip_transitive_deletes)


class RepositorySearchScore(BaseModel):
    repository = ForeignKeyField(Repository, unique=True)
    score = BigIntegerField(index=True, default=0)
    last_updated = DateTimeField(null=True)


class DeletedRepository(BaseModel):
    repository = ForeignKeyField(Repository, unique=True)
    marked = DateTimeField(default=datetime.now)
    original_name = CharField(index=True)
    queue_id = CharField(null=True, index=True)


class Star(BaseModel):
    user = ForeignKeyField(User)
    repository = ForeignKeyField(Repository)
    created = DateTimeField(default=datetime.now)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            # create a unique index on user and repository
            (("user", "repository"), True),
        )


class Role(BaseModel):
    name = CharField(index=True, unique=True)


class RepositoryPermission(BaseModel):
    team = ForeignKeyField(Team, null=True)
    user = QuayUserField(allows_robots=True, null=True)
    repository = ForeignKeyField(Repository)
    role = ForeignKeyField(Role)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            (("team", "repository"), True),
            (("user", "repository"), True),
        )


class PermissionPrototype(BaseModel):
    org = QuayUserField(index=True, backref="orgpermissionproto")
    uuid = CharField(default=uuid_generator, index=True)
    activating_user = QuayUserField(
        allows_robots=True, index=True, null=True, backref="userpermissionproto"
    )
    delegate_user = QuayUserField(allows_robots=True, backref="receivingpermission", null=True)
    delegate_team = ForeignKeyField(Team, backref="receivingpermission", null=True)
    role = ForeignKeyField(Role)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = ((("org", "activating_user"), False),)


class AccessTokenKind(BaseModel):
    name = CharField(unique=True, index=True)


class AccessToken(BaseModel):
    friendly_name = CharField(null=True)

    token_name = CharField(default=random_string_generator(length=32), unique=True, index=True)
    token_code = EncryptedCharField(default_token_length=32)

    repository = ForeignKeyField(Repository)
    created = DateTimeField(default=datetime.now)
    role = ForeignKeyField(Role)
    temporary = BooleanField(default=True)
    kind = ForeignKeyField(AccessTokenKind, null=True)

    def get_code(self):
        return self.token_name + self.token_code.decrypt()


class BuildTriggerService(BaseModel):
    name = CharField(index=True, unique=True)


class DisableReason(BaseModel):
    name = CharField(index=True, unique=True)


class RepositoryBuildTrigger(BaseModel):
    uuid = CharField(default=uuid_generator, index=True)
    service = ForeignKeyField(BuildTriggerService)
    repository = ForeignKeyField(Repository)
    connected_user = QuayUserField()

    secure_auth_token = EncryptedCharField(null=True)
    secure_private_key = EncryptedTextField(null=True)
    fully_migrated = BooleanField(default=False)

    config = TextField(default="{}")
    write_token = ForeignKeyField(AccessToken, null=True)
    pull_robot = QuayUserField(
        allows_robots=True, null=True, backref="triggerpullrobot", robot_null_delete=True
    )

    enabled = BooleanField(default=True)
    disabled_reason = EnumField(DisableReason, null=True)
    disabled_datetime = DateTimeField(default=datetime.utcnow, null=True, index=True)
    successive_failure_count = IntegerField(default=0)
    successive_internal_error_count = IntegerField(default=0)


class EmailConfirmation(BaseModel):
    code = CharField(default=random_string_generator(), unique=True, index=True)
    verification_code = CredentialField(null=True)
    user = QuayUserField()
    pw_reset = BooleanField(default=False)
    new_email = CharField(null=True)
    email_confirm = BooleanField(default=False)
    created = DateTimeField(default=datetime.now)


class ImageStorage(BaseModel):
    uuid = CharField(default=uuid_generator, index=True, unique=True)
    image_size = BigIntegerField(null=True)
    uncompressed_size = BigIntegerField(null=True)
    uploading = BooleanField(default=True, null=True)
    cas_path = BooleanField(default=True)
    content_checksum = CharField(null=True, index=True)


class ImageStorageTransformation(BaseModel):
    name = CharField(index=True, unique=True)


class ImageStorageSignatureKind(BaseModel):
    name = CharField(index=True, unique=True)


class ImageStorageSignature(BaseModel):
    storage = ForeignKeyField(ImageStorage)
    kind = ForeignKeyField(ImageStorageSignatureKind)
    signature = TextField(null=True)
    uploading = BooleanField(default=True, null=True)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = ((("kind", "storage"), True),)


class ImageStorageLocation(BaseModel):
    name = CharField(unique=True, index=True)


class ImageStoragePlacement(BaseModel):
    storage = ForeignKeyField(ImageStorage)
    location = ForeignKeyField(ImageStorageLocation)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            # An image can only be placed in the same place once
            (("storage", "location"), True),
        )


class UserRegion(BaseModel):
    user = QuayUserField(index=True, allows_robots=False)
    location = ForeignKeyField(ImageStorageLocation)

    indexes = ((("user", "location"), True),)


class Image(BaseModel):
    # This class is intentionally denormalized. Even though images are supposed
    # to be globally unique we can't treat them as such for permissions and
    # security reasons. So rather than Repository <-> Image being many to many
    # each image now belongs to exactly one repository.
    docker_image_id = CharField(index=True)
    repository = ForeignKeyField(Repository)

    # '/' separated list of ancestory ids, e.g. /1/2/6/7/10/
    ancestors = CharField(index=True, default="/", max_length=64535, null=True)

    storage = ForeignKeyField(ImageStorage, null=True)

    created = DateTimeField(null=True)
    comment = TextField(null=True)
    command = TextField(null=True)
    aggregate_size = BigIntegerField(null=True)
    v1_json_metadata = TextField(null=True)
    v1_checksum = CharField(null=True)

    security_indexed = BooleanField(default=False, index=True)
    security_indexed_engine = IntegerField(default=IMAGE_NOT_SCANNED_ENGINE_VERSION, index=True)

    # We use a proxy here instead of 'self' in order to disable the foreign key constraint
    parent = DeferredForeignKey("Image", null=True, backref="children")

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            # we don't really want duplicates
            (("repository", "docker_image_id"), True),
            (("security_indexed_engine", "security_indexed"), False),
        )

    def ancestor_id_list(self):
        """
        Returns an integer list of ancestor ids, ordered chronologically from root to direct parent.
        """
        return list(map(int, self.ancestors.split("/")[1:-1]))


@deprecated_model
class DerivedStorageForImage(BaseModel):
    source_image = ForeignKeyField(Image)
    derivative = ForeignKeyField(ImageStorage)
    transformation = ForeignKeyField(ImageStorageTransformation)
    uniqueness_hash = CharField(null=True)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = ((("source_image", "transformation", "uniqueness_hash"), True),)


@deprecated_model
class RepositoryTag(BaseModel):
    name = CharField()
    image = ForeignKeyField(Image)
    repository = ForeignKeyField(Repository)
    lifetime_start_ts = IntegerField(default=get_epoch_timestamp)
    lifetime_end_ts = IntegerField(null=True, index=True)
    hidden = BooleanField(default=False)
    reversion = BooleanField(default=False)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            (("repository", "name"), False),
            (("repository", "lifetime_start_ts"), False),
            (("repository", "lifetime_end_ts"), False),
            # This unique index prevents deadlocks when concurrently moving and deleting tags
            (("repository", "name", "lifetime_end_ts"), True),
        )


class BUILD_PHASE(object):
    """
    Build phases enum.
    """

    ERROR = "error"
    INTERNAL_ERROR = "internalerror"
    BUILD_SCHEDULED = "build-scheduled"
    UNPACKING = "unpacking"
    PULLING = "pulling"
    BUILDING = "building"
    PUSHING = "pushing"
    WAITING = "waiting"
    COMPLETE = "complete"
    CANCELLED = "cancelled"

    @classmethod
    def is_terminal_phase(cls, phase):
        return (
            phase == cls.COMPLETE
            or phase == cls.ERROR
            or phase == cls.INTERNAL_ERROR
            or phase == cls.CANCELLED
        )


class TRIGGER_DISABLE_REASON(object):
    """
    Build trigger disable reason enum.
    """

    BUILD_FALURES = "successive_build_failures"
    INTERNAL_ERRORS = "successive_build_internal_errors"
    USER_TOGGLED = "user_toggled"


class QueueItem(BaseModel):
    queue_name = CharField(index=True, max_length=1024)
    body = TextField()
    available_after = DateTimeField(default=datetime.utcnow)
    available = BooleanField(default=True)
    processing_expires = DateTimeField(null=True)
    retries_remaining = IntegerField(default=5)
    state_id = CharField(default=uuid_generator, index=True, unique=True)

    class Meta:
        database = db
        read_only_config = read_only_config
        only_save_dirty = True
        indexes = (
            (("processing_expires", "available"), False),
            (("processing_expires", "queue_name", "available"), False),
            (("processing_expires", "available_after", "retries_remaining", "available"), False),
            (
                (
                    "processing_expires",
                    "available_after",
                    "queue_name",
                    "retries_remaining",
                    "available",
                ),
                False,
            ),
        )

    def save(self, *args, **kwargs):
        # Always change the queue item's state ID when we update it.
        self.state_id = str(uuid.uuid4())
        super(QueueItem, self).save(*args, **kwargs)


class RepositoryBuild(BaseModel):
    uuid = CharField(default=uuid_generator, index=True)
    repository = ForeignKeyField(Repository)
    access_token = ForeignKeyField(AccessToken)
    resource_key = CharField(index=True, null=True)
    job_config = TextField()
    phase = CharField(default=BUILD_PHASE.WAITING)
    started = DateTimeField(default=datetime.now, index=True)
    display_name = CharField()
    trigger = ForeignKeyField(RepositoryBuildTrigger, null=True)
    pull_robot = QuayUserField(
        null=True, backref="buildpullrobot", allows_robots=True, robot_null_delete=True
    )
    logs_archived = BooleanField(default=False, index=True)
    queue_id = CharField(null=True, index=True)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            (("repository", "started", "phase"), False),
            (("started", "logs_archived", "phase"), False),
        )


class LogEntryKind(BaseModel):
    name = CharField(index=True, unique=True)


class LogEntry(BaseModel):
    id = BigAutoField()
    kind = ForeignKeyField(LogEntryKind)
    account = IntegerField(index=True, column_name="account_id")
    performer = IntegerField(index=True, null=True, column_name="performer_id")
    repository = IntegerField(index=True, null=True, column_name="repository_id")
    datetime = DateTimeField(default=datetime.now, index=True)
    ip = CharField(null=True)
    metadata_json = TextField(default="{}")

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            (("account", "datetime"), False),
            (("performer", "datetime"), False),
            (("repository", "datetime"), False),
            (("repository", "datetime", "kind"), False),
        )


class LogEntry2(BaseModel):
    """
    TEMP FOR QUAY.IO ONLY.

    DO NOT RELEASE INTO QUAY ENTERPRISE.
    """

    kind = ForeignKeyField(LogEntryKind)
    account = IntegerField(index=True, db_column="account_id")
    performer = IntegerField(index=True, null=True, db_column="performer_id")
    repository = IntegerField(index=True, null=True, db_column="repository_id")
    datetime = DateTimeField(default=datetime.now, index=True)
    ip = CharField(null=True)
    metadata_json = TextField(default="{}")

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            (("account", "datetime"), False),
            (("performer", "datetime"), False),
            (("repository", "datetime"), False),
            (("repository", "datetime", "kind"), False),
        )


class LogEntry3(BaseModel):
    id = BigAutoField()
    kind = IntegerField(db_column="kind_id")
    account = IntegerField(db_column="account_id")
    performer = IntegerField(null=True, db_column="performer_id")
    repository = IntegerField(null=True, db_column="repository_id")
    datetime = DateTimeField(default=datetime.now, index=True)
    ip = CharField(null=True)
    metadata_json = TextField(default="{}")

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            (("account", "datetime"), False),
            (("performer", "datetime"), False),
            (("repository", "datetime", "kind"), False),
        )


class RepositoryActionCount(BaseModel):
    repository = ForeignKeyField(Repository)
    count = IntegerField()
    date = DateField(index=True)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            # create a unique index on repository and date
            (("repository", "date"), True),
        )


class OAuthApplication(BaseModel):
    client_id = CharField(index=True, default=random_string_generator(length=20))
    secure_client_secret = EncryptedCharField(default_token_length=40, null=True)
    fully_migrated = BooleanField(default=False)

    redirect_uri = CharField()
    application_uri = CharField()
    organization = QuayUserField()

    name = CharField()
    description = TextField(default="")
    avatar_email = CharField(null=True, column_name="gravatar_email")


class OAuthAuthorizationCode(BaseModel):
    application = ForeignKeyField(OAuthApplication)

    code_name = CharField(index=True, unique=True)
    code_credential = CredentialField()

    scope = CharField()
    data = TextField()  # Context for the code, such as the user


class OAuthAccessToken(BaseModel):
    uuid = CharField(default=uuid_generator, index=True)
    application = ForeignKeyField(OAuthApplication)
    authorized_user = QuayUserField()
    scope = CharField()
    token_name = CharField(index=True, unique=True)
    token_code = CredentialField()

    token_type = CharField(default="Bearer")
    expires_at = DateTimeField()
    data = TextField()  # This is context for which this token was generated, such as the user


class NotificationKind(BaseModel):
    name = CharField(index=True, unique=True)


class Notification(BaseModel):
    uuid = CharField(default=uuid_generator, index=True)
    kind = ForeignKeyField(NotificationKind)
    target = QuayUserField(index=True, allows_robots=True)
    metadata_json = TextField(default="{}")
    created = DateTimeField(default=datetime.now, index=True)
    dismissed = BooleanField(default=False)
    lookup_path = CharField(null=True, index=True)


class ExternalNotificationEvent(BaseModel):
    name = CharField(index=True, unique=True)


class ExternalNotificationMethod(BaseModel):
    name = CharField(index=True, unique=True)


class RepositoryNotification(BaseModel):
    uuid = CharField(default=uuid_generator, index=True)
    repository = ForeignKeyField(Repository)
    event = EnumField(ExternalNotificationEvent)
    method = EnumField(ExternalNotificationMethod)
    title = CharField(null=True)
    config_json = TextField()
    event_config_json = TextField(default="{}")
    number_of_failures = IntegerField(default=0)


class RepositoryAuthorizedEmail(BaseModel):
    repository = ForeignKeyField(Repository)
    email = CharField()
    code = CharField(default=random_string_generator(), unique=True, index=True)
    confirmed = BooleanField(default=False)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            # create a unique index on email and repository
            (("email", "repository"), True),
        )


class UploadedBlob(BaseModel):
    """
    UploadedBlob tracks a recently uploaded blob and prevents it from being GCed
    while within the expiration window.
    """

    id = BigAutoField()
    repository = ForeignKeyField(Repository)
    blob = ForeignKeyField(ImageStorage)
    uploaded_at = DateTimeField(default=datetime.utcnow)
    expires_at = DateTimeField(index=True)


class BlobUpload(BaseModel):
    repository = ForeignKeyField(Repository)
    uuid = CharField(index=True, unique=True)
    byte_count = BigIntegerField(default=0)
    # TODO(kleesc): Verify that this is backward compatible with resumablehashlib
    sha_state = ResumableSHA256Field(null=True, default=rehash.sha256)
    location = ForeignKeyField(ImageStorageLocation)
    storage_metadata = JSONField(null=True, default={})
    chunk_count = IntegerField(default=0)
    uncompressed_byte_count = BigIntegerField(null=True)
    created = DateTimeField(default=datetime.now, index=True)
    piece_sha_state = ResumableSHA1Field(null=True)
    piece_hashes = Base64BinaryField(null=True)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            # create a unique index on email and repository
            (("repository", "uuid"), True),
        )


class QuayService(BaseModel):
    name = CharField(index=True, unique=True)


class QuayRegion(BaseModel):
    name = CharField(index=True, unique=True)


class QuayRelease(BaseModel):
    service = ForeignKeyField(QuayService)
    version = CharField()
    region = ForeignKeyField(QuayRegion)
    reverted = BooleanField(default=False)
    created = DateTimeField(default=datetime.now, index=True)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            # unique release per region
            (("service", "version", "region"), True),
            # get recent releases
            (("service", "region", "created"), False),
        )


@deprecated_model
class TorrentInfo(BaseModel):
    storage = ForeignKeyField(ImageStorage)
    piece_length = IntegerField()
    pieces = Base64BinaryField()

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            # we may want to compute the piece hashes multiple times with different piece lengths
            (("storage", "piece_length"), True),
        )


class ServiceKeyApprovalType(Enum):
    SUPERUSER = "Super User API"
    KEY_ROTATION = "Key Rotation"
    AUTOMATIC = "Automatic"


class ServiceKeyApproval(BaseModel):
    approver = QuayUserField(null=True)
    approval_type = CharField(index=True)
    approved_date = DateTimeField(default=datetime.utcnow)
    notes = TextField(default="")


class ServiceKey(BaseModel):
    name = CharField()
    kid = CharField(unique=True, index=True)
    service = CharField(index=True)
    jwk = JSONField()
    metadata = JSONField()
    created_date = DateTimeField(default=datetime.utcnow)
    expiration_date = DateTimeField(null=True)
    rotation_duration = IntegerField(null=True)
    approval = ForeignKeyField(ServiceKeyApproval, null=True)


class MediaType(BaseModel):
    """
    MediaType is an enumeration of the possible formats of various objects in the data model.
    """

    name = CharField(index=True, unique=True)


class Messages(BaseModel):
    content = TextField()
    uuid = CharField(default=uuid_generator, max_length=36, index=True)
    severity = CharField(default="info", index=True)
    media_type = ForeignKeyField(MediaType)


class LabelSourceType(BaseModel):
    """
    LabelSourceType is an enumeration of the possible sources for a label.
    """

    name = CharField(index=True, unique=True)
    mutable = BooleanField(default=False)


class Label(BaseModel):
    """
    Label represents user-facing metadata associated with another entry in the database (e.g. a
    Manifest).
    """

    uuid = CharField(default=uuid_generator, index=True, unique=True)
    key = CharField(index=True)
    value = TextField()
    media_type = EnumField(MediaType)
    source_type = EnumField(LabelSourceType)


class ApprBlob(BaseModel):
    """
    ApprBlob represents a content-addressable object stored outside of the database.
    """

    digest = CharField(index=True, unique=True)
    media_type = EnumField(MediaType)
    size = BigIntegerField()
    uncompressed_size = BigIntegerField(null=True)


class ApprBlobPlacementLocation(BaseModel):
    """
    ApprBlobPlacementLocation is an enumeration of the possible storage locations for ApprBlobs.
    """

    name = CharField(index=True, unique=True)


class ApprBlobPlacement(BaseModel):
    """
    ApprBlobPlacement represents the location of a Blob.
    """

    blob = ForeignKeyField(ApprBlob)
    location = EnumField(ApprBlobPlacementLocation)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = ((("blob", "location"), True),)


class ApprManifest(BaseModel):
    """
    ApprManifest represents the metadata and collection of blobs that comprise an Appr image.
    """

    digest = CharField(index=True, unique=True)
    media_type = EnumField(MediaType)
    manifest_json = JSONField()


class ApprManifestBlob(BaseModel):
    """
    ApprManifestBlob is a many-to-many relation table linking ApprManifests and ApprBlobs.
    """

    manifest = ForeignKeyField(ApprManifest, index=True)
    blob = ForeignKeyField(ApprBlob, index=True)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = ((("manifest", "blob"), True),)


class ApprManifestList(BaseModel):
    """
    ApprManifestList represents all of the various Appr manifests that compose an ApprTag.
    """

    digest = CharField(index=True, unique=True)
    manifest_list_json = JSONField()
    schema_version = CharField()
    media_type = EnumField(MediaType)


class ApprTagKind(BaseModel):
    """
    ApprTagKind is a enumtable to reference tag kinds.
    """

    name = CharField(index=True, unique=True)


class ApprTag(BaseModel):
    """
    ApprTag represents a user-facing alias for referencing an ApprManifestList.
    """

    name = CharField()
    repository = ForeignKeyField(Repository)
    manifest_list = ForeignKeyField(ApprManifestList, null=True)
    lifetime_start = BigIntegerField(default=get_epoch_timestamp_ms)
    lifetime_end = BigIntegerField(null=True, index=True)
    hidden = BooleanField(default=False)
    reverted = BooleanField(default=False)
    protected = BooleanField(default=False)
    tag_kind = EnumField(ApprTagKind)
    linked_tag = ForeignKeyField("self", null=True, backref="tag_parents")

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            (("repository", "name"), False),
            (("repository", "name", "hidden"), False),
            # This unique index prevents deadlocks when concurrently moving and deleting tags
            (("repository", "name", "lifetime_end"), True),
        )


ApprChannel = ApprTag.alias()


class ApprManifestListManifest(BaseModel):
    """
    ApprManifestListManifest is a many-to-many relation table linking ApprManifestLists and
    ApprManifests.
    """

    manifest_list = ForeignKeyField(ApprManifestList, index=True)
    manifest = ForeignKeyField(ApprManifest, index=True)
    operating_system = CharField(null=True)
    architecture = CharField(null=True)
    platform_json = JSONField(null=True)
    media_type = EnumField(MediaType)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = ((("manifest_list", "media_type"), False),)


class AppSpecificAuthToken(BaseModel):
    """
    AppSpecificAuthToken represents a token generated by a user for use with an external application
    where putting the user's credentials, even encrypted, is deemed too risky.
    """

    user = QuayUserField()
    uuid = CharField(default=uuid_generator, max_length=36, index=True)
    title = CharField()
    token_name = CharField(index=True, unique=True, default=random_string_generator(60))
    token_secret = EncryptedCharField(default_token_length=60)

    created = DateTimeField(default=datetime.now)
    expiration = DateTimeField(null=True)
    last_accessed = DateTimeField(null=True)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = ((("user", "expiration"), False),)


class Manifest(BaseModel):
    """
    Manifest represents a single manifest under a repository.

    Within a repository, there can only be one manifest with the same digest.
    """

    repository = ForeignKeyField(Repository)
    digest = CharField(index=True)
    media_type = EnumField(MediaType)
    manifest_bytes = TextField()

    config_media_type = CharField(null=True)
    layers_compressed_size = BigIntegerField(null=True)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            (("repository", "digest"), True),
            (("repository", "media_type"), False),
            (("repository", "config_media_type"), False),
        )


class TagKind(BaseModel):
    """
    TagKind describes the various kinds of tags that can be found in the registry.
    """

    name = CharField(index=True, unique=True)


class Tag(BaseModel):
    """
    Tag represents a user-facing alias for referencing a Manifest or as an alias to another tag.
    """

    name = CharField()
    repository = ForeignKeyField(Repository)
    manifest = ForeignKeyField(Manifest, null=True)
    lifetime_start_ms = BigIntegerField(default=get_epoch_timestamp_ms)
    lifetime_end_ms = BigIntegerField(null=True, index=True)
    hidden = BooleanField(default=False)
    reversion = BooleanField(default=False)
    tag_kind = EnumField(TagKind)
    linked_tag = ForeignKeyField("self", null=True, backref="tag_parents")

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            (("repository", "name"), False),
            (("repository", "name", "hidden"), False),
            (("repository", "name", "tag_kind"), False),
            (("repository", "lifetime_start_ms"), False),
            (("repository", "lifetime_end_ms"), False),
            # This unique index prevents deadlocks when concurrently moving and deleting tags
            (("repository", "name", "lifetime_end_ms"), True),
        )


class ManifestChild(BaseModel):
    """
    ManifestChild represents a relationship between a manifest and its child manifest(s).

    Multiple manifests can share the same children. Note that since Manifests are stored per-
    repository, the repository here is a bit redundant, but we do so to make cleanup easier.
    """

    repository = ForeignKeyField(Repository)
    manifest = ForeignKeyField(Manifest)
    child_manifest = ForeignKeyField(Manifest)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = (
            (("repository", "manifest"), False),
            (("repository", "child_manifest"), False),
            (("repository", "manifest", "child_manifest"), False),
            (("manifest", "child_manifest"), True),
        )


class ManifestLabel(BaseModel):
    """
    ManifestLabel represents a label applied to a Manifest, within a repository.

    Note that since Manifests are stored per-repository, the repository here is a bit redundant, but
    we do so to make cleanup easier.
    """

    repository = ForeignKeyField(Repository, index=True)
    manifest = ForeignKeyField(Manifest)
    label = ForeignKeyField(Label)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = ((("manifest", "label"), True),)


class ManifestBlob(BaseModel):
    """
    ManifestBlob represents a blob that is used by a manifest.
    """

    repository = ForeignKeyField(Repository, index=True)
    manifest = ForeignKeyField(Manifest)
    blob = ForeignKeyField(ImageStorage)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = ((("manifest", "blob"), True),)


class ManifestLegacyImage(BaseModel):
    """
    For V1-compatible manifests only, this table maps from the manifest to its associated Docker
    image.
    """

    repository = ForeignKeyField(Repository, index=True)
    manifest = ForeignKeyField(Manifest, unique=True)
    image = ForeignKeyField(Image)


@deprecated_model
class TagManifest(BaseModel):
    tag = ForeignKeyField(RepositoryTag, unique=True)
    digest = CharField(index=True)
    json_data = TextField()


@deprecated_model
class TagManifestToManifest(BaseModel):
    tag_manifest = ForeignKeyField(TagManifest, index=True, unique=True)
    manifest = ForeignKeyField(Manifest, index=True)
    broken = BooleanField(index=True, default=False)


@deprecated_model
class TagManifestLabel(BaseModel):
    repository = ForeignKeyField(Repository, index=True)
    annotated = ForeignKeyField(TagManifest, index=True)
    label = ForeignKeyField(Label)

    class Meta:
        database = db
        read_only_config = read_only_config
        indexes = ((("annotated", "label"), True),)


@deprecated_model
class TagManifestLabelMap(BaseModel):
    tag_manifest = ForeignKeyField(TagManifest, index=True)
    manifest = ForeignKeyField(Manifest, null=True, index=True)

    label = ForeignKeyField(Label, index=True)

    tag_manifest_label = ForeignKeyField(TagManifestLabel, index=True)
    manifest_label = ForeignKeyField(ManifestLabel, null=True, index=True)

    broken_manifest = BooleanField(index=True, default=False)


@deprecated_model
class TagToRepositoryTag(BaseModel):
    repository = ForeignKeyField(Repository, index=True)
    tag = ForeignKeyField(Tag, index=True, unique=True)
    repository_tag = ForeignKeyField(RepositoryTag, index=True, unique=True)


@unique
class RepoMirrorRuleType(IntEnum):
    """
    Types of mirroring rules.

    TAG_GLOB_CSV: Comma separated glob values (eg. "7.6,7.6-1.*")
    """

    TAG_GLOB_CSV = 1


class RepoMirrorRule(BaseModel):
    """
    Determines how a given Repository should be mirrored.
    """

    uuid = CharField(default=uuid_generator, max_length=36, index=True)
    repository = ForeignKeyField(Repository, index=True)
    creation_date = DateTimeField(default=datetime.utcnow)

    rule_type = ClientEnumField(RepoMirrorRuleType, default=RepoMirrorRuleType.TAG_GLOB_CSV)
    rule_value = JSONField()

    # Optional associations to allow the generation of a ruleset tree
    left_child = ForeignKeyField("self", null=True, backref="left_child")
    right_child = ForeignKeyField("self", null=True, backref="right_child")


@unique
class RepoMirrorType(IntEnum):
    """
    Types of repository mirrors.
    """

    PULL = 1  # Pull images from the external repo


@unique
class RepoMirrorStatus(IntEnum):
    """
    Possible statuses of repository mirroring.
    """

    FAIL = -1
    NEVER_RUN = 0
    SUCCESS = 1
    SYNCING = 2
    SYNC_NOW = 3


class RepoMirrorConfig(BaseModel):
    """
    Represents a repository to be mirrored and any additional configuration required to perform the
    mirroring.
    """

    repository = ForeignKeyField(Repository, index=True, unique=True, backref="mirror")
    creation_date = DateTimeField(default=datetime.utcnow)
    is_enabled = BooleanField(default=True)

    # Mirror Configuration
    mirror_type = ClientEnumField(RepoMirrorType, default=RepoMirrorType.PULL)
    internal_robot = QuayUserField(
        allows_robots=True,
        backref="mirrorpullrobot",
    )
    external_reference = CharField()
    external_registry_username = EncryptedCharField(max_length=2048, null=True)
    external_registry_password = EncryptedCharField(max_length=2048, null=True)
    external_registry_config = JSONField(default={})

    # Worker Queuing
    sync_interval = IntegerField()  # seconds between syncs
    sync_start_date = DateTimeField(null=True)  # next start time
    sync_expiration_date = DateTimeField(null=True)  # max duration
    sync_retries_remaining = IntegerField(default=3)
    sync_status = ClientEnumField(RepoMirrorStatus, default=RepoMirrorStatus.NEVER_RUN)
    sync_transaction_id = CharField(default=uuid_generator, max_length=36)

    # Tag-Matching Rules
    root_rule = ForeignKeyField(RepoMirrorRule)


@unique
class IndexStatus(IntEnum):
    """
    Possible statuses of manifest security scan progress.
    """

    MANIFEST_UNSUPPORTED = -2
    FAILED = -1
    IN_PROGRESS = 1
    COMPLETED = 2


@unique
class IndexerVersion(IntEnum):
    """
    Possible versions of security indexers.
    """

    V2 = 2
    V4 = 4


class ManifestSecurityStatus(BaseModel):
    """
    Represents the security scan status for a particular container image manifest.

    Intended to replace the `security_indexed` and `security_indexed_engine` fields
    on the `Image` model.
    """

    manifest = ForeignKeyField(Manifest, unique=True)
    repository = ForeignKeyField(Repository)
    index_status = ClientEnumField(IndexStatus)
    error_json = JSONField(default={})
    last_indexed = DateTimeField(default=datetime.utcnow, index=True)
    indexer_hash = CharField(max_length=128, index=True)
    indexer_version = ClientEnumField(IndexerVersion)
    metadata_json = JSONField(default={})


# Defines a map from full-length index names to the legacy names used in our code
# to meet length restrictions.
LEGACY_INDEX_MAP = {
    "derivedstorageforimage_source_image_id_transformation_id_uniqueness_hash": "uniqueness_hash",
    "queueitem_processing_expires_available_after_queue_name_retries_remaining_available": "queueitem_pe_aafter_qname_rremaining_available",
    "queueitem_processing_expires_available_after_retries_remaining_available": "queueitem_pexpires_aafter_rremaining_available",
}


appr_classes = set(
    [
        ApprTag,
        ApprTagKind,
        ApprBlobPlacementLocation,
        ApprManifestList,
        ApprManifestBlob,
        ApprBlob,
        ApprManifestListManifest,
        ApprManifest,
        ApprBlobPlacement,
    ]
)
v22_classes = set(
    [Manifest, ManifestLabel, ManifestBlob, ManifestLegacyImage, TagKind, ManifestChild, Tag]
)
transition_classes = set([TagManifestToManifest, TagManifestLabelMap, TagToRepositoryTag])

is_model = lambda x: inspect.isclass(x) and issubclass(x, BaseModel) and x is not BaseModel
all_models = [model[1] for model in inspect.getmembers(sys.modules[__name__], is_model)]
