import pytest
import json

from data import model
from endpoints.api.trigger_analyzer import is_parent
from endpoints.api.trigger import BuildTrigger
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


@pytest.mark.parametrize(
    "context,dockerfile_path,expected",
    [
        ("/", "/a/b", True),
        ("/a", "/a/b", True),
        ("/a/b", "/a/b", False),
        ("/a//", "/a/b", True),
        ("/a", "/a//b/c", True),
        ("/a//", "a/b", True),
        ("/a/b", "a/bc/d", False),
        ("/d", "/a/b", False),
        ("/a/b", "/a/b.c", False),
        ("/a/b", "/a/b/b.c", True),
        ("", "/a/b.c", False),
        ("/a/b", "", False),
        ("", "", False),
    ],
)
def test_super_user_build_endpoints(context, dockerfile_path, expected):
    assert is_parent(context, dockerfile_path) == expected


def test_enabled_disabled_trigger(app, client):
    trigger = model.build.list_build_triggers("devtable", "building")[0]
    trigger.config = json.dumps({"hook_id": "someid"})
    trigger.save()

    params = {
        "repository": "devtable/building",
        "trigger_uuid": trigger.uuid,
    }

    body = {
        "enabled": False,
    }

    with client_with_identity("devtable", client) as cl:
        result = conduct_api_call(cl, BuildTrigger, "PUT", params, body, 200).json
        assert not result["enabled"]

    body = {
        "enabled": True,
    }

    with client_with_identity("devtable", client) as cl:
        result = conduct_api_call(cl, BuildTrigger, "PUT", params, body, 200).json
        assert result["enabled"]
