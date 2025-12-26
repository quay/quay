import logging
import sys
import threading
from time import perf_counter
from typing import Any, List
from urllib.parse import urlparse

import ldap
from ldapurl import LDAPUrl  # type: ignore

from util.metrics.prometheus import (
    ldappool_auth_calls_failure,
    ldappool_auth_calls_success,
    ldappool_close_calls,
    ldappool_connect_calls,
    ldappool_connections_max,
)

logger = logging.getLogger(__name__)


class LDAPPoolExhausted(Exception):
    pass


class LDAPPoolDown(Exception):
    pass


class LDAPLockTimeout(Exception):
    pass


class Connection(object):
    # OPTIMIZATION: Use __slots__ to prevent creation of __dict__ per instance
    __slots__ = (
        "uri",
        "binddn",
        "bindpw",
        "params",
        "established",
        "inUse",
        "_whoami",
        "_conn",
        "_lock",
        "_lock_timeout",
        "_pool",
        "_health",
    )

    def __init__(self, uri: LDAPUrl, binddn: str, bindpw: str, params: dict = None):  # type: ignore
        self.uri = (
            LDAPUrl(uri, scope=ldap.SCOPE_SUBTREE, dn=binddn, cred=bindpw)
            if not isinstance(uri, LDAPUrl)
            else uri
        )
        self.binddn = binddn
        self.bindpw = bindpw
        self.params = params if params is not None else {"prewarm": False, "lock_timeout": 15.0}
        self.established = False
        self.inUse = False
        self._whoami = None
        self._conn = False
        self._lock = threading.Lock()
        self._lock_timeout = float(self.params.get("lock_timeout", 15.0))
        self._pool = None
        self._health = 0.0

        # Converted implicit string expression to log to avoid dead code
        logging.debug("ConnectionPool new Connection %s", self)

        if self.params.get("prewarm", False):
            self.__enter__()

    def __locktime(self):
        if self._health == 0.0:
            self._health = perf_counter()
            return True
        if (perf_counter() - self._health) < self._lock_timeout:
            return False
        return True

    def whoami(self):
        return self._whoami

    def __whoami(self):
        # do not stress the connection too often
        if self.__locktime():
            return
        for r in range(self.params.get("retries", 3)):
            try:
                self._whoami = self._conn.whoami_s()
                return
            except ldap.SERVER_DOWN as ldaperr:
                logging.exception("__whoami ConnectionPool %s", ldaperr)
                self.established = False
                # just catch that error until we finish iterating
                try:
                    self.__enter__()
                except ldap.LDAPError:
                    self.giveback()
                    continue
        self.giveback()
        raise ldap.SERVER_DOWN(f"max retries {self.params.get('retries', 3)} reached") from None

    @property
    def conn(self):
        if self._conn is False:
            self.__enter__()
        try:
            if self.established:
                self.__whoami()
        except ldap.SERVER_DOWN as ldaperr:
            self.established = False
            self.giveback()
            raise LDAPPoolDown(
                f"could not establish connection with {self.uri.initializeUrl()}"
                + f" with max retries of {self.params.get('retries', 3)}"
            ) from ldaperr
        return self._conn

    def __lock_acquire(self):
        try:
            if self._lock.acquire(blocking=True, timeout=1):
                return True
        except Exception as lockerr:
            return False
        return False

    def __lock_release(self):
        try:
            self._lock.release()
            return True
        except Exception as lockerr:
            return False
        return False

    def authenticate(self, binddn: str, bindpw: str):
        if not self.__lock_acquire():
            raise LDAPLockTimeout()

        try:
            self.conn.simple_bind_s(binddn, bindpw)
            ldappool_auth_calls_success.inc()
            if not self.__lock_release():
                raise LDAPLockTimeout()
        except ldap.INVALID_CREDENTIALS as ldaperr:
            # rollback auth anyway
            ldappool_auth_calls_failure.inc()
            self.__lock_release()
            self.__authenticate__()
            raise
        except ldap.SERVER_DOWN as ldaperr:
            # free connection
            self.__lock_release()
            raise
        # rollback auth anyway
        self.__authenticate__()
        return True

    def __authenticate__(self):
        try:
            self.conn.simple_bind_s(self.binddn, self.bindpw)
            ldappool_auth_calls_success.inc()
            logging.debug("__whoami from __authenticate__")
            self.__whoami()
        except ldap.INVALID_CREDENTIALS as ldaperr:
            ldappool_auth_calls_failure.inc()
            logging.info(ldaperr)
            raise
        except ldap.SERVER_DOWN as ldaperr:
            self.giveback()
            raise

    def __set_connection_parameters__(self):
        try:
            self._conn.set_option(ldap.OPT_REFERRALS, self.params.get("referrals", False))
            self._conn.set_option(
                ldap.OPT_NETWORK_TIMEOUT, self.params.get("network_timeout", 10.0)
            )
            self._conn.set_option(ldap.OPT_TIMEOUT, self.params.get("timeout", 10.0))
            self._conn.set_option(ldap.OPT_X_KEEPALIVE_IDLE, self.params.get("keepalive_idle", 10))
            self._conn.set_option(
                ldap.OPT_X_KEEPALIVE_INTERVAL, self.params.get("keepalive_interval", 5)
            )
            self._conn.set_option(
                ldap.OPT_X_KEEPALIVE_PROBES, self.params.get("keepalive_probes", 3)
            )
            self._conn.set_option(ldap.OPT_RESTART, ldap.OPT_ON)
            if self.params.get("allow_tls_fallback", False):
                self._conn.set_option(ldap.OPT_X_TLS_TRY, 1)
            self._conn.set_option(ldap.OPT_X_TLS_NEWCTX, ldap.OPT_OFF)
        except Exception as connerr:
            logging.error("cannot set LDAP option %s", connerr)

    def __enter__(self):
        self.inUse = True
        if not self.established:
            logging.debug("ConnectionPool %s initializing LDAP %s", self, self.uri.initializeUrl())
            try:
                ldappool_connect_calls.inc()
                self._conn = ldap.initialize(self.uri.initializeUrl())
                self.__set_connection_parameters__()
                if self.params.get("autoBind", False):
                    # Fixed implicit string to log
                    logging.debug(
                        "ConnectionPool %s autoBind with %s password %s",
                        self,
                        self.binddn,
                        "x" * len(self.bindpw),
                    )
                self.__authenticate__()
            except Exception as ldaperr:
                logging.error(ldaperr)  # Fixed implicit string to log
                self.giveback()
                raise ldaperr
        self.established = True
        return self.conn

    def giveback(self, force=False):
        try:
            if force:
                try:
                    self._conn.unbind_s()
                except Exception as ldaperr:
                    logging.error("ConnectionPool unbind connection %s exception %s", self, ldaperr)
                self.inUse = False
                return

            if self.params.get("autoBind", False):
                if not self.params.get("keep", False):
                    logging.debug("ConnectionPool unbind connection %s", self)
                    try:
                        self._conn.unbind_s()
                    except Exception as ldaperr:
                        logging.error(
                            "ConnectionPool unbind connection %s exception %s", self, ldaperr
                        )
            self.inUse = False
        except AttributeError:
            self.inUse = False

    def __del__(self):
        try:
            self.giveback()
        except Exception:
            pass

    def __exit__(self, type, value, traceback):
        self.giveback()
        if self._pool is not None and not self.params.get("keep", False):
            self._pool.delete(self)

    def __eq__(self, other):
        if isinstance(other, Connection):
            return self.uri.initializeUrl() == other.uri.initializeUrl()
        return False

    def __hash__(self):
        return hash(self.uri.initializeUrl())

    def set_uri(self, uri: LDAPUrl):
        self.uri = LDAPUrl(uri) if not isinstance(uri, LDAPUrl) else uri
        return True

    def set_binddn(self, binddn: str):
        self.binddn = binddn
        return True

    def set_bindpw(self, bindpw: str):
        self.bindpw = bindpw
        return True

    def set_credentials(self, binddn: str, bindpw: str):
        self.set_binddn(binddn)
        self.set_bindpw(bindpw)
        return True


class ConnectionPool(object):
    # OPTIMIZATION: Use __slots__
    __slots__ = ("uri", "binddn", "bindpw", "params", "max", "_lock", "_pool", "_context_conn")

    def __init__(
        self,
        uri: LDAPUrl = None,  # Avoid mutable default, handled below or in field def
        binddn: str = "",
        bindpw: str = "",
        params: dict = None,  # type: ignore
        max: int = 50,
    ):
        uri = (
            LDAPUrl(uri, scope=ldap.SCOPE_SUBTREE, dn=binddn, cred=bindpw)
            if not isinstance(uri, LDAPUrl)
            else uri
        )
        self.uri = uri if isinstance(uri, LDAPUrl) else LDAPUrl("ldap:///")
        self.binddn = binddn
        self.bindpw = bindpw
        self.params = params if params is not None else {}
        self.max = int(max)
        self._lock = threading.Lock()
        self._pool: List[Any] = []
        logging.debug("ConnectionPool %s starting with %s connections", self, self.max)
        ldappool_connections_max.set(self.max)
        if self.params.get("prewarm", False):
            self.scale()

    @property
    def basedn(self):
        return self.uri.dn

    @property
    def scope(self):
        return self.uri.scope

    @property
    def filter(self):
        return self.uri.filterstr

    @property
    def attributes(self):
        return self.uri.attrs

    @property
    def extensions(self):
        return self.uri.extensions

    def set_uri(self, uri: LDAPUrl):
        if not isinstance(uri, LDAPUrl):
            uri = LDAPUrl(uri)

        if not self._lock.acquire(timeout=1):
            raise LDAPLockTimeout("Could not acquire pool lock")
        try:
            # OPTIMIZATION: Replace map/lambda/filter with explicit loop
            # This avoids creating a temporary list in memory just for side effects
            if len(self._pool) > 0:
                for cp in self._pool:
                    if cp.uri != uri:
                        cp.set_uri(uri)
                        cp.giveback(force=True)
        finally:
            self._lock.release()

        self.uri = uri
        return True

    def set_binddn(self, binddn: str):
        # OPTIMIZATION: Replace map/lambda/filter with explicit loop
        if len(self._pool) > 0:
            for cp in self._pool:
                if cp.binddn != binddn:
                    cp.set_binddn(binddn)
                    cp.giveback(force=True)

        self.binddn = binddn
        return True

    def set_bindpw(self, bindpw: str):
        # OPTIMIZATION: Replace map/lambda/filter with explicit loop
        if len(self._pool) > 0:
            for cp in self._pool:
                if cp.bindpw != bindpw:
                    cp.set_bindpw(bindpw)
                    cp.giveback(force=True)

        self.bindpw = bindpw
        return True

    def set_credentials(self, binddn: str, bindpw: str):
        self.set_binddn(binddn)
        self.set_bindpw(bindpw)
        return True

    def scale(self):
        for _ in range(self.max - len(self._pool)):
            self.put(
                Connection(
                    uri=self.uri,
                    binddn=self.binddn,
                    bindpw=self.bindpw,
                    params=self.params,
                )
            )

    def __enter__(self):
        if len(self._pool) == 0:
            self.scale()
        self._context_conn = self.get()
        return self._context_conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, "_context_conn") and self._context_conn is not None:
            self.put(self._context_conn)
            self._context_conn = None
            ldappool_close_calls.inc()
        return False

    def __revamp__(self):
        logger.error("LDAP revamping pool")
        for stale in self._pool:
            try:
                logger.error(f"LDAP revamp conn {stale}")
                self.delete(stale)
            except Exception as ldaperr:
                logger.error(f"LDAP cannot revamp pool {ldaperr}")
                continue
        self.scale()

    def ping(self):
        conn = self.get()
        try:
            # whoami_s is a lightweight operation to verify connectivity
            conn.conn.whoami_s()
            self.put(conn)
            return True
        except ldap.SERVER_DOWN:
            conn.inUse = False
            self.put(conn)
            self.__revamp__()
            raise
        except ldap.LDAPError as e:
            self.put(conn)
            logging.exception("LDAP ping failed for %s", self.uri.initializeUrl())
            raise LDAPPoolDown(f"Server unreachable: {self.uri.initializeUrl()}") from e

    def get(self, binddn: str = "", bindpw: str = ""):
        if len(self._pool) == 0:
            self.scale()
        if not self._lock.acquire(timeout=1):
            raise LDAPLockTimeout("LDAP Could not acquire pool lock")
        if len(self._pool) == 0:
            self._lock.release()
            logging.warning(
                "LDAP max connections %s reached, consider increasing pool size", self.max
            )
            self.__revamp__()
            raise LDAPPoolExhausted(f"max connections {self.max} reached")
        try:
            con = next((c for c in self._pool if not c.inUse), None)
            if con is None:
                raise IndexError()
        except IndexError:
            self._lock.release()
            logging.warning("all connections %s in use, consider increasing pool size", self.max)
            logging.warning(f"pool = {self._pool}")
            self.__revamp__()
            raise LDAPPoolExhausted(
                f"all connections {self.max} in use, consider increasing pool size"
            )
        con.inUse = True
        self._lock.release()
        if all([binddn != "", bindpw != ""]):
            try:
                con.authenticate(binddn, bindpw)
            except ldap.INVALID_CREDENTIALS:
                con.inUse = False
                self.put(con)
                raise
            except ldap.SERVER_DOWN:
                con.inUse = False
                self.put(con)
                self.__revamp__()
                raise
            except LDAPPoolExhausted as ldaperr:
                con.inUse = False
                self.put(con)
                self.__revamp__()
                raise
        return con

    def put(self, connection):
        if not self._lock.acquire(timeout=1):
            raise LDAPLockTimeout("Could not acquire pool lock")
        if connection.inUse:
            connection.giveback()
        if connection not in self._pool:
            self._pool.append(connection)
        connection._pool = self
        self._lock.release()
        return True

    def status(self):
        if not self._lock.acquire(timeout=1):
            raise LDAPLockTimeout("Could not acquire pool lock")
        for p in self._pool:
            if p.inUse:
                if sys.getrefcount(p) < 4:
                    p.giveback()
            logging.info("Id %s inUse %s %s %s", p, p.inUse, p.established, p.whoami())
        self._lock.release()

    def delete(self, connection, force=True):
        if not self._lock.acquire(timeout=1):
            raise LDAPLockTimeout("Could not acquire pool lock")
        if connection in self._pool:
            if any([not self.params.get("keep", False), force]):
                self._pool.remove(connection)
                ldappool_close_calls.inc()
                del connection
        self._lock.release()

    def __len__(self):
        return len(self._pool)
