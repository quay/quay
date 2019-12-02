import pytest
from mock import Mock

import util
from data import model
from endpoints.api.repoemail_models_interface import RepositoryAuthorizedEmail
from endpoints.api.repoemail_models_pre_oci import pre_oci_model


@pytest.fixture
def get_monkeypatch(monkeypatch):
    return monkeypatch


def return_none(name, repo, email):
    return None


def get_return_mock(mock):
    def return_mock(name, repo, email):
        return mock

    return return_mock


def test_get_email_authorized_for_repo(get_monkeypatch):
    mock = Mock()

    get_monkeypatch.setattr(model.repository, "get_email_authorized_for_repo", mock)

    pre_oci_model.get_email_authorized_for_repo("namespace_name", "repository_name", "email")

    mock.assert_called_once_with("namespace_name", "repository_name", "email")


def test_get_email_authorized_for_repo_return_none(get_monkeypatch):
    get_monkeypatch.setattr(model.repository, "get_email_authorized_for_repo", return_none)

    repo = pre_oci_model.get_email_authorized_for_repo("namespace_name", "repository_name", "email")

    assert repo is None


def test_get_email_authorized_for_repo_return_repo(get_monkeypatch):
    mock = Mock(confirmed=True, code="code")
    get_monkeypatch.setattr(
        model.repository, "get_email_authorized_for_repo", get_return_mock(mock)
    )

    actual = pre_oci_model.get_email_authorized_for_repo(
        "namespace_name", "repository_name", "email"
    )

    assert actual == RepositoryAuthorizedEmail(
        "email", "repository_name", "namespace_name", True, "code"
    )


def test_create_email_authorization_for_repo(get_monkeypatch):
    mock = Mock()
    get_monkeypatch.setattr(model.repository, "create_email_authorization_for_repo", mock)

    pre_oci_model.create_email_authorization_for_repo("namespace_name", "repository_name", "email")

    mock.assert_called_once_with("namespace_name", "repository_name", "email")


def test_create_email_authorization_for_repo_return_none(get_monkeypatch):
    get_monkeypatch.setattr(model.repository, "create_email_authorization_for_repo", return_none)

    assert (
        pre_oci_model.create_email_authorization_for_repo(
            "namespace_name", "repository_name", "email"
        )
        is None
    )


def test_create_email_authorization_for_repo_return_mock(get_monkeypatch):
    mock = Mock()
    get_monkeypatch.setattr(
        model.repository, "create_email_authorization_for_repo", get_return_mock(mock)
    )

    assert (
        pre_oci_model.create_email_authorization_for_repo(
            "namespace_name", "repository_name", "email"
        )
        is not None
    )


def test_create_email_authorization_for_repo_return_value(get_monkeypatch):
    mock = Mock(confirmed=False, code="code")

    get_monkeypatch.setattr(
        model.repository, "create_email_authorization_for_repo", get_return_mock(mock)
    )

    actual = pre_oci_model.create_email_authorization_for_repo(
        "namespace_name", "repository_name", "email"
    )
    assert actual == RepositoryAuthorizedEmail(
        "email", "repository_name", "namespace_name", False, "code"
    )
