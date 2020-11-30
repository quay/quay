import pytest

from data import model
from data.database import RepositoryState
from endpoints.api.build import RepositoryBuildList, RepositoryBuildResource
from endpoints.api.manifest import RepositoryManifestLabels, ManageRepositoryManifestLabel
from endpoints.api.tag import RepositoryTag, RestoreTag
from endpoints.api.trigger import (
    BuildTrigger,
    BuildTriggerSubdirs,
    BuildTriggerActivate,
    BuildTriggerAnalyze,
    ActivateBuildTrigger,
    BuildTriggerFieldValues,
    BuildTriggerSources,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *

BUILD_ARGS = {"build_uuid": "1234"}
IMAGE_ARGS = {"imageid": "1234", "image_id": 1234}
MANIFEST_ARGS = {"manifestref": "sha256:abcd1234"}
LABEL_ARGS = {"manifestref": "sha256:abcd1234", "labelid": "1234"}
NOTIFICATION_ARGS = {"uuid": "1234"}
TAG_ARGS = {"tag": "foobar"}
TRIGGER_ARGS = {"trigger_uuid": "1234"}
FIELD_ARGS = {"trigger_uuid": "1234", "field_name": "foobar"}


@pytest.mark.parametrize(
    "state",
    [
        RepositoryState.MIRROR,
        RepositoryState.READ_ONLY,
    ],
)
@pytest.mark.parametrize(
    "resource, method, params",
    [
        (RepositoryBuildList, "post", None),
        (RepositoryBuildResource, "delete", BUILD_ARGS),
        (RepositoryManifestLabels, "post", MANIFEST_ARGS),
        (ManageRepositoryManifestLabel, "delete", LABEL_ARGS),
        (RepositoryTag, "put", TAG_ARGS),
        (RepositoryTag, "delete", TAG_ARGS),
        (RestoreTag, "post", TAG_ARGS),
        (BuildTrigger, "delete", TRIGGER_ARGS),
        (BuildTriggerSubdirs, "post", TRIGGER_ARGS),
        (BuildTriggerActivate, "post", TRIGGER_ARGS),
        (BuildTriggerAnalyze, "post", TRIGGER_ARGS),
        (ActivateBuildTrigger, "post", TRIGGER_ARGS),
        (BuildTriggerFieldValues, "post", FIELD_ARGS),
        (BuildTriggerSources, "post", TRIGGER_ARGS),
    ],
)
def test_disallowed_for_nonnormal(state, resource, method, params, client):
    namespace = "devtable"
    repository = "somenewstaterepo"

    devtable = model.user.get_user("devtable")
    repo = model.repository.create_repository(namespace, repository, devtable)
    repo.state = state
    repo.save()

    params = params or {}
    params["repository"] = "%s/%s" % (namespace, repository)

    with client_with_identity("devtable", client) as cl:
        conduct_api_call(cl, resource, method, params, {}, 503)
