import random

from collections import namedtuple
from contextlib import contextmanager

from peewee import Model, SENTINEL, OperationalError, Proxy

from data.decorators import is_deprecated_model


ReadOnlyConfig = namedtuple("ReadOnlyConfig", ["is_readonly", "read_replicas"])


class ReadOnlyModeException(Exception):
    """
    Exception raised if a write operation was attempted when in read only mode.
    """


_FORCE_MASTER_COUNTER_ATTRIBUTE = "_force_master_nesting"


@contextmanager
def disallow_replica_use(db):
    """ When used, any queries run under this context manager will hit the master
        node and be disallowed from using the read replica(s). NOTE: This means if
        the master node is unavailable, the underlying queries will *fail*.
    """
    database = db.obj
    counter = getattr(database._state, _FORCE_MASTER_COUNTER_ATTRIBUTE, 0)
    setattr(database._state, _FORCE_MASTER_COUNTER_ATTRIBUTE, counter + 1)
    try:
        yield
    finally:
        counter = getattr(database._state, _FORCE_MASTER_COUNTER_ATTRIBUTE, 0)
        assert counter > 0
        setattr(database._state, _FORCE_MASTER_COUNTER_ATTRIBUTE, counter - 1)


class AutomaticFailoverWrapper(object):
    """
    Class which wraps a peewee database driver and (optionally) a second driver.

    When executing SQL, if an OperationalError occurs, if a second driver is given, the query is
    attempted again on the fallback DB. Otherwise, the exception is raised.
    """

    def __init__(self, primary_db, fallback_db=None):
        self._primary_db = primary_db
        self._fallback_db = fallback_db

    def __getattr__(self, attribute):
        if attribute != "execute_sql" and hasattr(self._primary_db, attribute):
            return getattr(self._primary_db, attribute)

        return getattr(self, attribute)

    def execute(self, query, commit=SENTINEL, **context_options):
        ctx = self.get_sql_context(**context_options)
        sql, params = ctx.sql(query).query()
        return self.execute_sql(sql, params, commit=commit)

    def execute_sql(self, sql, params=None, commit=SENTINEL):
        try:
            return self._primary_db.execute_sql(sql, params, commit)
        except OperationalError:
            if self._fallback_db is not None:
                try:
                    return self._fallback_db.execute_sql(sql, params, commit)
                except OperationalError:
                    raise


class ReadReplicaSupportedModel(Model):
    """
    Base model for peewee data models that support using a read replica for SELECT requests not
    under transactions, and automatic failover to the master if the read replica fails.

    Read-only queries are initially attempted on one of the read replica databases
    being used; if an OperationalError occurs when attempting to invoke the query,
    then the failure is logged and the query is retried on the database master.

    Queries that are non-SELECTs (or under transactions) are always tried on the
    master.

    If the system is configured into read only mode, then all non-read-only queries
    will raise a ReadOnlyModeException.
    """

    @classmethod
    def _read_only_config(cls):
        read_only_config = getattr(cls._meta, "read_only_config", None)
        if read_only_config is None:
            return ReadOnlyConfig(False, [])

        if isinstance(read_only_config, Proxy) and read_only_config.obj is None:
            return ReadOnlyConfig(False, [])

        return read_only_config.obj or ReadOnlyConfig(False, [])

    @classmethod
    def _in_readonly_mode(cls):
        return cls._read_only_config().is_readonly

    @classmethod
    def _select_database(cls):
        """
        Selects a read replica database if we're configured to support read replicas.

        Otherwise, selects the master database.
        """
        # Select the master DB if read replica support is not enabled.
        read_only_config = cls._read_only_config()
        if not read_only_config.read_replicas:
            return cls._meta.database

        # Select the master DB if we're ever under a transaction.
        if cls._meta.database.transaction_depth() > 0:
            return cls._meta.database

        # Select if forced.
        if getattr(cls._meta.database._state, _FORCE_MASTER_COUNTER_ATTRIBUTE, 0) > 0:
            return cls._meta.database

        # Otherwise, return a read replica database with auto-retry onto the main database.
        replicas = read_only_config.read_replicas
        selected_read_replica = replicas[random.randrange(len(replicas))]
        return AutomaticFailoverWrapper(selected_read_replica, cls._meta.database)

    @classmethod
    def select(cls, *args, **kwargs):
        query = super(ReadReplicaSupportedModel, cls).select(*args, **kwargs)
        query._database = cls._select_database()
        return query

    @classmethod
    def insert(cls, *args, **kwargs):
        if is_deprecated_model(cls):
            raise Exception("Attempt to write to deprecated model %s" % cls)

        query = super(ReadReplicaSupportedModel, cls).insert(*args, **kwargs)
        if cls._in_readonly_mode():
            raise ReadOnlyModeException()
        return query

    @classmethod
    def update(cls, *args, **kwargs):
        query = super(ReadReplicaSupportedModel, cls).update(*args, **kwargs)
        if cls._in_readonly_mode():
            raise ReadOnlyModeException()
        return query

    @classmethod
    def delete(cls, *args, **kwargs):
        query = super(ReadReplicaSupportedModel, cls).delete(*args, **kwargs)
        if cls._in_readonly_mode():
            raise ReadOnlyModeException()
        return query

    @classmethod
    def raw(cls, *args, **kwargs):
        query = super(ReadReplicaSupportedModel, cls).raw(*args, **kwargs)
        if query._sql.lower().startswith("select "):
            query._database = cls._select_database()
        elif cls._in_readonly_mode():
            raise ReadOnlyModeException()
        elif query._sql.lower().startswith("insert "):
            if is_deprecated_model(cls):
                raise Exception("Attempt to write to deprecated model %s" % cls)

        return query
