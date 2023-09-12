from test.fixtures import *

import pytest

from data import model
from endpoints.api.build import (
    RepositoryBuildList,
    RepositoryBuildLogs,
    RepositoryBuildResource,
    RepositoryBuildStatus,
)
from endpoints.api.manifest import (
    ManageRepositoryManifestLabel,
    RepositoryManifestLabels,
)
from endpoints.api.repository import Repository
from endpoints.api.repositorynotification import (
    RepositoryNotification,
    RepositoryNotificationList,
    TestRepositoryNotification,
)
from endpoints.api.secscan import RepositoryManifestSecurity
from endpoints.api.signing import RepositorySignatures
from endpoints.api.tag import ListRepositoryTags, RepositoryTag, RestoreTag
from endpoints.api.test.shared import conduct_api_call
from endpoints.api.trigger import (
    ActivateBuildTrigger,
    BuildTrigger,
    BuildTriggerActivate,
    BuildTriggerAnalyze,
    BuildTriggerFieldValues,
    BuildTriggerList,
    BuildTriggerSourceNamespaces,
    BuildTriggerSources,
    BuildTriggerSubdirs,
    TriggerBuildList,
)
from endpoints.test.shared import client_with_identity

BUILD_ARGS = {"build_uuid": "1234"}
IMAGE_ARGS = {"imageid": "1234", "image_id": 1234}
MANIFEST_ARGS = {"manifestref": "sha256:abcd1234"}
LABEL_ARGS = {"manifestref": "sha256:abcd1234", "labelid": "1234"}
NOTIFICATION_ARGS = {"uuid": "1234"}
TAG_ARGS = {"tag": "foobar"}
TRIGGER_ARGS = {"trigger_uuid": "1234"}
FIELD_ARGS = {"trigger_uuid": "1234", "field_name": "foobar"}


@pytest.mark.parametrize(
    "resource, method, params",
    [
        (RepositoryBuildList, "get", None),
        (RepositoryBuildList, "post", None),
        (RepositoryBuildResource, "get", BUILD_ARGS),
        (RepositoryBuildResource, "delete", BUILD_ARGS),
        (RepositoryBuildStatus, "get", BUILD_ARGS),
        (RepositoryBuildLogs, "get", BUILD_ARGS),
        (RepositoryManifestLabels, "get", MANIFEST_ARGS),
        (RepositoryManifestLabels, "post", MANIFEST_ARGS),
        (ManageRepositoryManifestLabel, "get", LABEL_ARGS),
        (ManageRepositoryManifestLabel, "delete", LABEL_ARGS),
        (RepositoryNotificationList, "get", None),
        (RepositoryNotificationList, "post", None),
        (RepositoryNotification, "get", NOTIFICATION_ARGS),
        (RepositoryNotification, "delete", NOTIFICATION_ARGS),
        (RepositoryNotification, "post", NOTIFICATION_ARGS),
        (TestRepositoryNotification, "post", NOTIFICATION_ARGS),
        (RepositoryManifestSecurity, "get", MANIFEST_ARGS),
        (RepositorySignatures, "get", None),
        (ListRepositoryTags, "get", None),
        (RepositoryTag, "put", TAG_ARGS),
        (RepositoryTag, "delete", TAG_ARGS),
        (RestoreTag, "post", TAG_ARGS),
        (BuildTriggerList, "get", None),
        (BuildTrigger, "get", TRIGGER_ARGS),
        (BuildTrigger, "delete", TRIGGER_ARGS),
        (BuildTriggerSubdirs, "post", TRIGGER_ARGS),
        (BuildTriggerActivate, "post", TRIGGER_ARGS),
        (BuildTriggerAnalyze, "post", TRIGGER_ARGS),
        (ActivateBuildTrigger, "post", TRIGGER_ARGS),
        (TriggerBuildList, "get", TRIGGER_ARGS),
        (BuildTriggerFieldValues, "post", FIELD_ARGS),
        (BuildTriggerSources, "post", TRIGGER_ARGS),
        (BuildTriggerSourceNamespaces, "get", TRIGGER_ARGS),
    ],
)
def test_disallowed_for_apps(resource, method, params, app):
    namespace = "devtable"
    repository = "someapprepo"

    devtable = model.user.get_user("devtable")
    model.repository.create_repository(namespace, repository, devtable, repo_kind="application")

    params = params or {}
    params["repository"] = "%s/%s" % (namespace, repository)

    with client_with_identity("devtable", app) as cl:
        conduct_api_call(cl, resource, method, params, None, 501)
