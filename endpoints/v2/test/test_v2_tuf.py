import pytest
import flask

from flask_principal import Identity, Principal
from mock import Mock

from auth import permissions
from endpoints.v2.v2auth import _get_tuf_root
from test import testconfig
from util.security.registry_jwt import QUAY_TUF_ROOT, SIGNER_TUF_ROOT, DISABLED_TUF_ROOT


def admin_identity(namespace, reponame):
    identity = Identity("admin")
    identity.provides.add(permissions._RepositoryNeed(namespace, reponame, "admin"))
    identity.provides.add(permissions._OrganizationRepoNeed(namespace, "admin"))
    return identity


def write_identity(namespace, reponame):
    identity = Identity("writer")
    identity.provides.add(permissions._RepositoryNeed(namespace, reponame, "write"))
    identity.provides.add(permissions._OrganizationRepoNeed(namespace, "write"))
    return identity


def read_identity(namespace, reponame):
    identity = Identity("reader")
    identity.provides.add(permissions._RepositoryNeed(namespace, reponame, "read"))
    identity.provides.add(permissions._OrganizationRepoNeed(namespace, "read"))
    return identity


def app_with_principal():
    app = flask.Flask(__name__)
    app.config.from_object(testconfig.TestConfig())
    principal = Principal(app)
    return app, principal


@pytest.mark.parametrize(
    "identity,expected",
    [
        (Identity("anon"), QUAY_TUF_ROOT),
        (read_identity("namespace", "repo"), QUAY_TUF_ROOT),
        (read_identity("different", "repo"), QUAY_TUF_ROOT),
        (admin_identity("different", "repo"), QUAY_TUF_ROOT),
        (write_identity("different", "repo"), QUAY_TUF_ROOT),
        (admin_identity("namespace", "repo"), SIGNER_TUF_ROOT),
        (write_identity("namespace", "repo"), SIGNER_TUF_ROOT),
    ],
)
def test_get_tuf_root(identity, expected):
    app, principal = app_with_principal()
    with app.test_request_context("/"):
        principal.set_identity(identity)
        actual = _get_tuf_root(Mock(), "namespace", "repo")
        assert actual == expected, "should be %s, but was %s" % (expected, actual)


@pytest.mark.parametrize(
    "trust_enabled,tuf_root", [(True, QUAY_TUF_ROOT), (False, DISABLED_TUF_ROOT),]
)
def test_trust_disabled(trust_enabled, tuf_root):
    app, principal = app_with_principal()
    with app.test_request_context("/"):
        principal.set_identity(read_identity("namespace", "repo"))
        actual = _get_tuf_root(Mock(trust_enabled=trust_enabled), "namespace", "repo")
        assert actual == tuf_root, "should be %s, but was %s" % (tuf_root, actual)
