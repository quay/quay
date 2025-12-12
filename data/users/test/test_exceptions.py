import logging
from typing import List

import ldap
import pytest

from data.users.externalldap import (
    LDAP_CONNECTION_ERRORS,
    LDAPUsers,
    _log_ldap_error,
    logger,
)


class ExceptionLogHandler(logging.StreamHandler):
    on_same_line = False
    content = []  # type: List[str]

    def emit(self, record):
        try:
            msg = self.format(record)
            self.content.append(msg)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


exceptHandler = ExceptionLogHandler()
logger.addHandler(exceptHandler)


def test_ldap_user_search():
    # reset content from log
    exceptHandler.content = []  # type: List[str]
    user = LDAPUsers(
        ldap_uri="invalid",
        base_dn=["dc=example", "dc=com"],
        admin_dn="cn=invalid,dc=example,dc=com",
        admin_passwd="stillinvalid",
        user_rdn="ou=people,dc=example,dc=com",
        uid_attr="uid",
        email_attr="mail",
        timeout=1,
        network_timeout=1,
    )

    def raiseException(ex):
        raise ex(*[{"info": "Can't contact LDAP server", "desc": "Can't contact LDAP server"}])

    user._ldap.get_connection = lambda: raiseException(ldap.SERVER_DOWN)
    assert user._ldap_user_search(None) == (None, "Empty username/email")
    assert user._ldap_user_search("someone") == (None, "Invalid username or password.")
    assert exceptHandler.content[0] == "SERVER_DOWN -1 Can't contact LDAP server"
    # reset content from log
    exceptHandler.content = []  # type: List[str]


def test_ldap_warning_exceptions_user_search():
    # reset content from log
    exceptHandler.content = []  # type: List[str]
    for exception in (
        (ldap.AUTH_UNKNOWN, -6),
        (ldap.CONFIDENTIALITY_REQUIRED, 13),
        (ldap.CONSTRAINT_VIOLATION, 19),
        (ldap.INVALID_DN_SYNTAX, 34),
        (ldap.INVALID_SYNTAX, 21),
        (ldap.SERVER_DOWN, -1),
        (ldap.STRONG_AUTH_NOT_SUPPORTED, 7),
        (ldap.STRONG_AUTH_REQUIRED, 8),
        (ldap.UNAVAILABLE, 52),
        (ldap.UNWILLING_TO_PERFORM, 53),
        (ldap.CONTROL_NOT_FOUND, -13),
        (ldap.INAPPROPRIATE_AUTH, 48),
        (ldap.INSUFFICIENT_ACCESS, 50),
    ):
        user = LDAPUsers(
            ldap_uri="ldaps://localhost",
            base_dn=["dc=example", "dc=com"],
            admin_dn="cn=invalid,dc=example,dc=com",
            admin_passwd="stillinvalid",
            user_rdn="ou=people,dc=example,dc=com",
            uid_attr="uid",
            email_attr="mail",
            timeout=1,
            network_timeout=1,
        )

        def raiseException(ex):
            raise ex(*[{"info": "test", "desc": "test"}])

        user._ldap.get_connection = lambda: raiseException(exception[0])
        assert user._ldap_user_search("someone") == (None, "Invalid username or password.")
        assert exceptHandler.content[0] == f"{exception[0].__name__} {exception[1]} test"
        # reset content from log
        exceptHandler.content = []  # type: List[str]


def test_ldap_warning_exceptions_ping():
    # reset content from log
    exceptHandler.content = []
    for exception in (
        (ldap.AUTH_UNKNOWN, -6),
        (ldap.CONFIDENTIALITY_REQUIRED, 13),
        (ldap.CONSTRAINT_VIOLATION, 19),
        (ldap.INVALID_DN_SYNTAX, 34),
        (ldap.INVALID_SYNTAX, 21),
        (ldap.SERVER_DOWN, -1),
        (ldap.STRONG_AUTH_NOT_SUPPORTED, 7),
        (ldap.STRONG_AUTH_REQUIRED, 8),
        (ldap.UNAVAILABLE, 52),
        (ldap.UNWILLING_TO_PERFORM, 53),
        (ldap.CONTROL_NOT_FOUND, -13),
        (ldap.INAPPROPRIATE_AUTH, 48),
        (ldap.INSUFFICIENT_ACCESS, 50),
    ):
        user = LDAPUsers(
            ldap_uri="ldaps://localhost",
            base_dn=["dc=example", "dc=com"],
            admin_dn="cn=invalid,dc=example,dc=com",
            admin_passwd="stillinvalid",
            user_rdn="ou=people,dc=example,dc=com",
            uid_attr="uid",
            email_attr="mail",
            timeout=1,
            network_timeout=1,
        )

        def raiseException(ex):
            raise ex(*[{"info": "test", "desc": "test"}])

        user._ldap.get_connection = lambda: raiseException(exception[0])
        assert user.ping() == (False, f"{exception[0].__name__} {exception[0].errnum} test")
        assert exceptHandler.content[0] == "Exception when trying to health check LDAP"
        assert exceptHandler.content[1] == f"{exception[0].__name__} {exception[0].errnum} test"
        # reset content from log
        exceptHandler.content = []  # type: List[str]


def test_ldap_warning_exception_at_least_one_user_exists():
    # reset content from log
    exceptHandler.content = []  # type: List[str]

    for exception in (
        (ldap.AUTH_UNKNOWN, -6),
        (ldap.CONFIDENTIALITY_REQUIRED, 13),
        (ldap.CONSTRAINT_VIOLATION, 19),
        (ldap.INVALID_DN_SYNTAX, 34),
        (ldap.INVALID_SYNTAX, 21),
        (ldap.SERVER_DOWN, -1),
        (ldap.STRONG_AUTH_NOT_SUPPORTED, 7),
        (ldap.STRONG_AUTH_REQUIRED, 8),
        (ldap.UNAVAILABLE, 52),
        (ldap.UNWILLING_TO_PERFORM, 53),
        (ldap.CONTROL_NOT_FOUND, -13),
        (ldap.INAPPROPRIATE_AUTH, 48),
        (ldap.INSUFFICIENT_ACCESS, 50),
    ):
        user = LDAPUsers(
            ldap_uri="ldaps://localhost",
            base_dn=["dc=example", "dc=com"],
            admin_dn="cn=invalid,dc=example,dc=com",
            admin_passwd="stillinvalid",
            user_rdn="ou=people,dc=example,dc=com",
            uid_attr="uid",
            email_attr="mail",
            timeout=1,
            network_timeout=1,
        )

        def raiseException(ex):
            raise ex(*[{"info": "test", "desc": "test"}])

        user._ldap.get_connection = lambda: raiseException(exception[0])
        assert user.at_least_one_user_exists() == (None, "LDAP Admin dn or password is invalid")
        assert exceptHandler.content[0] == f"{exception[0].__name__} {exception[1]} test"
        # reset content from log
        exceptHandler.content = []  # type: List[str]


def test_ldap_warning_exception_verify_credentials():
    # reset content from log
    exceptHandler.content = []  # type: List[str]

    for exception in (
        (ldap.AUTH_UNKNOWN, -6),
        (ldap.CONFIDENTIALITY_REQUIRED, 13),
        (ldap.CONSTRAINT_VIOLATION, 19),
        (ldap.INVALID_DN_SYNTAX, 34),
        (ldap.INVALID_SYNTAX, 21),
        (ldap.SERVER_DOWN, -1),
        (ldap.STRONG_AUTH_NOT_SUPPORTED, 7),
        (ldap.STRONG_AUTH_REQUIRED, 8),
        (ldap.UNAVAILABLE, 52),
        (ldap.UNWILLING_TO_PERFORM, 53),
        (ldap.CONTROL_NOT_FOUND, -13),
        (ldap.INAPPROPRIATE_AUTH, 48),
        (ldap.INSUFFICIENT_ACCESS, 50),
    ):
        user = LDAPUsers(
            ldap_uri="ldaps://localhost",
            base_dn=["dc=example", "dc=com"],
            admin_dn="cn=invalid,dc=example,dc=com",
            admin_passwd="stillinvalid",
            user_rdn="ou=people,dc=example,dc=com",
            uid_attr="uid",
            email_attr="mail",
            timeout=1,
            network_timeout=1,
        )

        def raiseException(ex):
            raise ex(*[{"info": "test", "desc": "test"}])

        user._ldap.get_connection = lambda: raiseException(exception[0])
        assert user.verify_credentials("someone", "changeme") == (
            None,
            "Invalid username or password.",
        )
        assert exceptHandler.content[0] == f"{exception[0].__name__} {exception[1]} test"
        # reset content from log
        exceptHandler.content = []  # type: List[str]


def test_ldap_catchall_exception_verify_credentials():
    # reset content from log
    exceptHandler.content = []  # type: List[str]
    user = LDAPUsers(
        ldap_uri="ldaps://localhost",
        base_dn=["dc=example", "dc=com"],
        admin_dn="cn=invalid,dc=example,dc=com",
        admin_passwd="stillinvalid",
        user_rdn="ou=people,dc=example,dc=com",
        uid_attr="uid",
        email_attr="mail",
        timeout=1,
        network_timeout=1,
    )

    def raiseException(*args, **kwargs):
        logger.debug("debuglog level only")
        raise IOError("debuglog level only")

    user._ldap.get_connection = raiseException
    with pytest.raises(IOError) as excinfo:
        user.verify_credentials("someone", "changeme")
    assert str(excinfo.value) == "debuglog level only"
    assert exceptHandler.content == []
    logger.setLevel(logging.DEBUG)
    with pytest.raises(IOError) as excinfo:
        user.verify_credentials("someone", "changeme")
    assert str(excinfo.value) == "debuglog level only"
    assert exceptHandler.content[0] == "debuglog level only"
    # reset content from log
    exceptHandler.content = []  # type: List[str]


def test_ldap_log_ldap_error():
    # reset content from log
    exceptHandler.content = []  # type: List[str]

    for ldapexception in LDAP_CONNECTION_ERRORS:
        with pytest.raises(ldapexception) as ldaperr:
            raise ldapexception("Unittest")
        # pytest.raises ExceptionInfo Object -> value Exception
        args = _log_ldap_error(ldaperr.value, details=True, additional="Unittest context")
        assert exceptHandler.content[0] == "Unittest context"
        assert (
            exceptHandler.content[1] == f"{ldapexception.__name__} {ldapexception.errnum} Unittest"
        )
        assert args == f"{ldapexception.__name__} {ldapexception.errnum} Unittest"
        # reset content from log
        exceptHandler.content = []  # type: List[str]
