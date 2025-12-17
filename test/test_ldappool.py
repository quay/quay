from time import sleep, time

import ldap
import pytest


class MockLDAPPool:
    def __init__(self):
        self.directory = {
            "uid=quay,ou=users,dc=example,dc=com": {
                "cn": ["Quay binduser"],
                "sn": ["Quay"],
                "uid": ["quay"],
                "mail": ["quay@example.com"],
                "objectClass": ["inetOrgPerson"],
                "userPassword": ["special"],
            },
            "uid=jdoe,ou=users,dc=example,dc=com": {
                "cn": ["John Doe"],
                "sn": ["Doe"],
                "uid": ["jdoe"],
                "mail": ["jdoe@example.com"],
                "objectClass": ["inetOrgPerson"],
                "userPassword": ["changeme"],
            },
        }
        self.bound_user = None

    def initialize(self, uri, trace_level=0):
        self.simple_bind_s("uid=quay,ou=users,dc=example,dc=com", "special")
        return self

    def set_option(self, key, value):
        return

    def simple_bind_s(self, who, cred):
        if who in self.directory and self.directory[who].get("userPassword")[0] == cred:
            self.bound_user = who
            return (97, [])  # LDAP success code
        raise ldap.INVALID_CREDENTIALS("Invalid Credentials")

    def search_s(self, base, scope, filterstr="(objectClass=*)", attrlist=None):
        results = []
        for dn, attrs in self.directory.items():
            if dn.endswith(base):
                if "=" in filterstr:
                    attr, value = filterstr.strip("()").split("=")
                    if attr in attrs and value in attrs[attr]:
                        results.append((dn, attrs))
                else:
                    results.append((dn, attrs))
        return results

    def whoami_s(self):
        return self.bound_user

    def unbind_s(self):
        return (97, [])


import ldappool
from ldappool import Connection, ConnectionPool, LDAPLockTimeout, LDAPPoolExhausted


@pytest.fixture
def mock_ldap(monkeypatch):
    """Fixture to provide a fresh MockLDAPPool instance for each test."""
    mock = MockLDAPPool()
    monkeypatch.setattr(ldappool.ldap, "initialize", mock.initialize)
    return mock


@pytest.fixture
def mock_ldap_server_down(monkeypatch):
    """Fixture to provide a fresh MockLDAPPool instance for each test."""

    def server_down(*args, **kwargs):
        raise ldap.SERVER_DOWN()

    mock = MockLDAPPool()
    monkeypatch.setattr(ldappool.ldap, "initialize", mock.initialize)
    monkeypatch.setattr(ldappool.Connection, "_Connection__whoami", server_down)
    monkeypatch.setattr(ldappool.Connection, "authenticate", server_down)
    return mock


outage = [ldap.SERVER_DOWN, ldap.SERVER_DOWN]


@pytest.fixture
def mock_ldap_server_outage(monkeypatch):
    """Fixture to provide a fresh MockLDAPPool instance for each test."""

    def server_down(*args, **kwargs):
        if len(outage) > 0:
            raise outage.pop()()
        return True

    mock = MockLDAPPool()
    monkeypatch.setattr(ldappool.ldap, "initialize", mock.initialize)
    monkeypatch.setattr(ldappool.Connection, "_Connection__whoami", server_down)
    return mock


def test_pool_authentication(mock_ldap):
    pool = ConnectionPool(
        "ldaps://ldap.example.com:636/dc=example,dc=com?uid,mail,memberOf?sub?(objectClass=*)",
        binddn="uid=quay,ou=users,dc=example,dc=com",
        bindpw="special",
        max=1,
    )
    assert len(pool) == 0
    conn = pool.get()
    assert len(pool) == 1
    assert conn.inUse == True
    assert conn.established == False
    assert conn._lock.locked() == False
    assert conn.conn.whoami_s() == "uid=quay,ou=users,dc=example,dc=com"

    assert conn.authenticate("uid=jdoe,ou=users,dc=example,dc=com", "changeme") == True
    with pytest.raises(ldap.INVALID_CREDENTIALS):
        conn.authenticate("uid=jdoe,ou=users,dc=example,dc=com", "changemeXXX")
    assert conn.conn.whoami_s() == "uid=quay,ou=users,dc=example,dc=com"
    assert len(pool) == 1
    assert conn.inUse == True
    assert conn.established == True
    assert conn._lock.locked() == False


def test_pool_exhausted(mock_ldap):
    pool = ConnectionPool(
        "ldaps://ldap.example.com:636/dc=example,dc=com?uid,mail,memberOf?sub?(objectClass=*)",
        binddn="uid=quay,ou=users,dc=example,dc=com",
        bindpw="special",
        max=1,
    )
    assert len(pool) == 0
    conn1 = pool.get()
    assert len(pool) == 1
    assert conn1.inUse == True
    assert conn1.established == False
    assert conn1._lock.locked() == False
    assert conn1.conn.whoami_s() == "uid=quay,ou=users,dc=example,dc=com"

    with pytest.raises(LDAPPoolExhausted):
        conn2 = pool.get()
        conn2.authenticate("", "")


def test_pool_exhausted_butnotblocked(mock_ldap):
    pool = ConnectionPool(
        "ldaps://ldap.example.com:636/dc=example,dc=com?uid,mail,memberOf?sub?(objectClass=*)",
        binddn="uid=quay,ou=users,dc=example,dc=com",
        bindpw="special",
        max=1,
    )
    assert len(pool) == 0
    conn1 = pool.get()
    assert len(pool) == 1
    assert conn1.inUse == True
    assert conn1.established == False
    assert conn1._lock.locked() == False
    assert conn1.conn.whoami_s() == "uid=quay,ou=users,dc=example,dc=com"

    with pytest.raises(LDAPPoolExhausted):
        conn2 = pool.get()

    assert conn1.authenticate("uid=jdoe,ou=users,dc=example,dc=com", "changeme") == True
    assert conn1.conn.whoami_s() == "uid=quay,ou=users,dc=example,dc=com"
    conn1.giveback()
    conn2 = pool.get()
    assert conn2.authenticate("uid=jdoe,ou=users,dc=example,dc=com", "changeme") == True
    assert conn2.conn.whoami_s() == "uid=quay,ou=users,dc=example,dc=com"


def test_pool_exhausted_butnotblocked_even_on_autherror(mock_ldap):
    pool = ConnectionPool(
        "ldaps://ldap.example.com:636/dc=example,dc=com?uid,mail,memberOf?sub?(objectClass=*)",
        binddn="uid=quay,ou=users,dc=example,dc=com",
        bindpw="special",
        max=1,
    )
    assert len(pool) == 0
    conn1 = pool.get()
    assert len(pool) == 1
    assert conn1.inUse == True
    assert conn1.established == False
    assert conn1._lock.locked() == False
    assert conn1.conn.whoami_s() == "uid=quay,ou=users,dc=example,dc=com"

    with pytest.raises(LDAPPoolExhausted):
        conn2 = pool.get()

    assert conn1.authenticate("uid=jdoe,ou=users,dc=example,dc=com", "changeme") == True
    assert conn1.conn.whoami_s() == "uid=quay,ou=users,dc=example,dc=com"
    conn1.giveback()
    conn2 = pool.get()
    with pytest.raises(ldap.INVALID_CREDENTIALS):
        conn2.authenticate("uid=jdoe,ou=users,dc=example,dc=com", "changemeXXX")
    conn2.giveback()
    conn3 = pool.get()
    assert conn3.authenticate("uid=jdoe,ou=users,dc=example,dc=com", "changeme") == True
    assert conn3.conn.whoami_s() == "uid=quay,ou=users,dc=example,dc=com"
    assert len(pool) == 1
    assert conn3.inUse == True
    assert conn3.established == True
    assert conn3._lock.locked() == False


def test_pool_prewarm(mock_ldap):
    pool = ConnectionPool(
        "ldaps://ldap.example.com:636/dc=example,dc=com?uid,mail,memberOf?sub?(objectClass=*)",
        binddn="uid=quay,ou=users,dc=example,dc=com",
        bindpw="special",
        max=3,
        params={"prewarm": True},
    )
    assert len(pool) == 1
    conn = pool.get()
    assert conn.inUse == True
    assert conn.established == True
    assert conn._lock.locked() == False
    assert conn.conn.whoami_s() == "uid=quay,ou=users,dc=example,dc=com"


def test_connection_locking(mock_ldap):
    pool = ConnectionPool(
        "ldaps://ldap.example.com:636/dc=example,dc=com?uid,mail,memberOf?sub?(objectClass=*)",
        binddn="uid=quay,ou=users,dc=example,dc=com",
        bindpw="special",
        max=1,
        params={"prewarm": True, "lock_timeout": 3},
    )
    conn = pool.get()
    assert conn._Connection__lock_acquire() == True
    locktimestart = time()
    with pytest.raises(LDAPLockTimeout):
        conn.authenticate("invalid", "invalid")
    locktimeend = time()
    assert locktimeend - locktimestart < 3
    assert conn._Connection__lock_release() == True
    assert conn.authenticate("uid=jdoe,ou=users,dc=example,dc=com", "changeme")


def test_connection_server_down_prewarm(mock_ldap_server_down):
    with pytest.raises(ldap.SERVER_DOWN):
        pool = ConnectionPool(
            "ldaps://ldap.example.com:636/dc=example,dc=com?uid,mail,memberOf?sub?(objectClass=*)",
            binddn="uid=quay,ou=users,dc=example,dc=com",
            bindpw="special",
            max=1,
            params={"prewarm": True, "lock_timeout": 3},
        )


def test_connection_server_down(mock_ldap_server_down):
    with pytest.raises(ldap.SERVER_DOWN):
        pool = ConnectionPool(
            "ldaps://ldap.example.com:636/dc=example,dc=com?uid,mail,memberOf?sub?(objectClass=*)",
            binddn="uid=quay,ou=users,dc=example,dc=com",
            bindpw="special",
            max=1,
            params={"prewarm": False, "lock_timeout": 3},
        )
        conn = pool.get()
        conn.authenticate("", "")


def test_connection_server_down_recover(mock_ldap_server_outage):
    pool = ConnectionPool(
        "ldaps://ldap.example.com:636/dc=example,dc=com?uid,mail,memberOf?sub?(objectClass=*)",
        binddn="uid=quay,ou=users,dc=example,dc=com",
        bindpw="special",
        max=1,
        params={"prewarm": False, "lock_timeout": 3},
    )
    oiter = len(outage)
    for _ in range(oiter):
        with pytest.raises((ldap.SERVER_DOWN, LDAPPoolExhausted)):
            conn = pool.get()
            conn.authenticate("uid=jdoe,ou=users,dc=example,dc=com", "changeme")
    for _ in range(oiter):
        try:
            conn = pool.get()
        except (ldap.SERVER_DOWN, LDAPPoolExhausted):
            continue
    assert conn.authenticate("uid=jdoe,ou=users,dc=example,dc=com", "changeme") == True
    assert outage == []
    with pytest.raises(ldap.INVALID_CREDENTIALS):
        conn.authenticate("uid=jdoe,ou=users,dc=example,dc=com", "xxx")


def test_connection_locks(mock_ldap):
    pool = ConnectionPool(
        "ldaps://ldap.example.com:636/dc=example,dc=com?uid,mail,memberOf?sub?(objectClass=*)",
        binddn="uid=quay,ou=users,dc=example,dc=com",
        bindpw="special",
        max=1,
        params={"prewarm": False, "lock_timeout": 1},
    )
    conn1 = pool.get()
    assert conn1._Connection__lock_acquire() == True
    assert conn1._Connection__lock_acquire() == False

    assert conn1._Connection__lock_release() == True
    assert conn1._Connection__lock_release() == False

    conn1.giveback()

    conn1 = pool.get()
    assert conn1._Connection__locktime() == True
    assert conn1._health > 0.0
    assert conn1._Connection__locktime() == False
    sleep(1)
    assert conn1._Connection__locktime() == True


def test_ldapurl_parsing(mock_ldap):
    pool = ConnectionPool(
        "ldaps://ldap.example.com:636/dc=example,dc=com?uid,mail?sub?(&(memberOf=user)(!(loginShell=/sbin/nologin)))"
        + "?uid=quay,ou=users,dc=example,dc=com,X-BINDPW=changeme",
        binddn="uid=quay,ou=users,dc=example,dc=com",
        bindpw="special",
        max=1,
    )
    conn = pool.get()

    assert pool.basedn == "dc=example,dc=com"
    assert pool.scope == 2
    assert sorted(pool.attributes) == sorted(["uid", "mail"])
    assert pool.uri.urlscheme == "ldaps"
    assert pool.uri.hostport == "ldap.example.com:636"
    assert pool.filter == "(&(memberOf=user)(!(loginShell=/sbin/nologin)))"
    assert sorted(pool.extensions) == sorted(["X-BINDPW", "dc", "ou", "uid"])

    assert conn.uri.urlscheme == "ldaps"
    assert conn.uri.hostport == "ldap.example.com:636"
    assert conn.uri.filterstr == "(&(memberOf=user)(!(loginShell=/sbin/nologin)))"
    assert conn.uri.hostport == "ldap.example.com:636"
    assert conn.uri.scope == 2
    assert sorted(conn.uri.extensions) == sorted(["X-BINDPW", "dc", "ou", "uid"])
