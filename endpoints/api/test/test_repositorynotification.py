import pytest
from mock import MagicMock, Mock

import endpoints.api.repositorynotification_models_interface as iface
from endpoints.api.repositorynotification import (
    RepositoryNotification,
    RepositoryNotificationList,
    TestRepositoryNotification,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


@pytest.fixture()
def authd_client(app):
    with client_with_identity("devtable", app) as cl:
        yield cl


def mock_get_notification(uuid):
    mock_notification = MagicMock(iface.RepositoryNotification)
    if uuid == "exists":
        mock_notification.return_value = iface.RepositoryNotification(
            "exists",
            "title",
            "event_name",
            "method_name",
            "config_json",
            "event_config_json",
            2,
        )
    else:
        mock_notification.return_value = None
    return mock_notification


@pytest.mark.parametrize(
    "namespace,repository,body,expected_code",
    [
        (
            "devtable",
            "simple",
            dict(
                config={"url": "http://example.com"},
                event="repo_push",
                method="webhook",
                eventConfig={},
                title="test",
            ),
            201,
        ),
        (
            "devtable",
            "simple",
            dict(
                config={"url": "http://example.com"},
                event="repo_mirror_sync_started",
                method="webhook",
                eventConfig={},
                title="test",
            ),
            201,
        ),
        (
            "devtable",
            "simple",
            dict(
                config={"url": "http://example.com"},
                event="repo_mirror_sync_success",
                method="webhook",
                eventConfig={},
                title="test",
            ),
            201,
        ),
        (
            "devtable",
            "simple",
            dict(
                config={"url": "http://example.com"},
                event="repo_mirror_sync_failed",
                method="webhook",
                eventConfig={},
                title="test",
            ),
            201,
        ),
    ],
)
def test_create_repo_notification(namespace, repository, body, expected_code, authd_client):
    params = {"repository": namespace + "/" + repository}
    conduct_api_call(
        authd_client, RepositoryNotificationList, "POST", params, body, expected_code=expected_code
    )


def test_create_vulnerability_notification_with_tag_regex(authd_client):
    params = {"repository": "devtable/simple"}
    body = {
        "config": {"url": "http://example.com"},
        "event": "vulnerability_found",
        "method": "webhook",
        "eventConfig": {"level": "1", "tag-regex": "v2"},
        "title": "v2 vulnerabilities",
    }

    response = conduct_api_call(
        authd_client, RepositoryNotificationList, "POST", params, body, expected_code=201
    ).json

    assert response["event_config"] == {"level": "1", "tag-regex": "v2"}


@pytest.mark.parametrize("tag_regex", [None, "", "   "])
def test_create_vulnerability_notification_accepts_empty_tag_regex(authd_client, tag_regex):
    params = {"repository": "devtable/simple"}
    body = {
        "config": {"url": "http://example.com"},
        "event": "vulnerability_found",
        "method": "webhook",
        "eventConfig": {"level": "1", "tag-regex": tag_regex},
        "title": "all tag vulnerabilities",
    }

    conduct_api_call(
        authd_client, RepositoryNotificationList, "POST", params, body, expected_code=201
    )


@pytest.mark.parametrize("tag_regex", ["[v2", 123])
def test_create_vulnerability_notification_rejects_invalid_tag_regex(authd_client, tag_regex):
    params = {"repository": "devtable/simple"}
    body = {
        "config": {"url": "http://example.com"},
        "event": "vulnerability_found",
        "method": "webhook",
        "eventConfig": {"level": "1", "tag-regex": tag_regex},
        "title": "invalid tag regex",
    }

    conduct_api_call(
        authd_client, RepositoryNotificationList, "POST", params, body, expected_code=400
    )


@pytest.mark.parametrize("namespace,repository,expected_code", [("devtable", "simple", 200)])
def test_list_repo_notifications(namespace, repository, expected_code, authd_client):
    params = {"repository": namespace + "/" + repository}
    resp = conduct_api_call(
        authd_client, RepositoryNotificationList, "GET", params, expected_code=expected_code
    ).json
    assert len(resp["notifications"]) > 0


@pytest.mark.parametrize(
    "namespace,repository,uuid,expected_code",
    [
        ("devtable", "simple", "exists", 200),
        ("devtable", "simple", "not found", 404),
    ],
)
def test_get_repo_notification(
    namespace, repository, uuid, expected_code, authd_client, monkeypatch
):
    monkeypatch.setattr(
        "endpoints.api.repositorynotification.model.get_repo_notification",
        mock_get_notification(uuid),
    )
    params = {"repository": namespace + "/" + repository, "uuid": uuid}
    conduct_api_call(
        authd_client, RepositoryNotification, "GET", params, expected_code=expected_code
    )


@pytest.mark.parametrize(
    "namespace,repository,uuid,expected_code",
    [
        ("devtable", "simple", "exists", 204),
        ("devtable", "simple", "not found", 400),
    ],
)
def test_delete_repo_notification(
    namespace, repository, uuid, expected_code, authd_client, monkeypatch
):
    monkeypatch.setattr(
        "endpoints.api.repositorynotification.model.delete_repo_notification",
        mock_get_notification(uuid),
    )
    params = {"repository": namespace + "/" + repository, "uuid": uuid}
    conduct_api_call(
        authd_client, RepositoryNotification, "DELETE", params, expected_code=expected_code
    )


@pytest.mark.parametrize(
    "namespace,repository,uuid,expected_code",
    [
        ("devtable", "simple", "exists", 204),
        ("devtable", "simple", "not found", 400),
    ],
)
def test_reset_repo_noticiation(
    namespace, repository, uuid, expected_code, authd_client, monkeypatch
):
    monkeypatch.setattr(
        "endpoints.api.repositorynotification.model.reset_notification_number_of_failures",
        mock_get_notification(uuid),
    )
    params = {"repository": namespace + "/" + repository, "uuid": uuid}
    conduct_api_call(
        authd_client, RepositoryNotification, "POST", params, expected_code=expected_code
    )


@pytest.mark.parametrize(
    "namespace,repository,uuid,expected_code",
    [
        ("devtable", "simple", "exists", 200),
        ("devtable", "simple", "not found", 400),
    ],
)
def test_test_repo_notification(
    namespace, repository, uuid, expected_code, authd_client, monkeypatch
):
    monkeypatch.setattr(
        "endpoints.api.repositorynotification.model.queue_test_notification",
        mock_get_notification(uuid),
    )
    params = {"repository": namespace + "/" + repository, "uuid": uuid}
    conduct_api_call(
        authd_client, TestRepositoryNotification, "POST", params, expected_code=expected_code
    )
