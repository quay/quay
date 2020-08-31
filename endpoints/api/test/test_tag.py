import pytest

from playhouse.test_utils import assert_query_count

from data.registry_model import registry_model
from data.database import Manifest

from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from endpoints.api.tag import RepositoryTag, RestoreTag, ListRepositoryTags, RepositoryTagImages

from test.fixtures import *


@pytest.mark.parametrize(
    "expiration_time, expected_status",
    [
        (None, 201),
        ("aksdjhasd", 400),
    ],
)
def test_change_tag_expiration_default(expiration_time, expected_status, client, app):
    with client_with_identity("devtable", client) as cl:
        params = {
            "repository": "devtable/simple",
            "tag": "latest",
        }

        request_body = {
            "expiration": expiration_time,
        }

        conduct_api_call(cl, RepositoryTag, "put", params, request_body, expected_status)


def test_change_tag_expiration(client, app):
    with client_with_identity("devtable", client) as cl:
        params = {
            "repository": "devtable/simple",
            "tag": "latest",
        }

        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag = registry_model.get_repo_tag(repo_ref, "latest")

        updated_expiration = tag.lifetime_start_ts + 60 * 60 * 24

        request_body = {
            "expiration": updated_expiration,
        }

        conduct_api_call(cl, RepositoryTag, "put", params, request_body, 201)
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        assert tag.lifetime_end_ts == updated_expiration


@pytest.mark.parametrize(
    "image_exists,test_tag,expected_status",
    [
        (True, "-INVALID-TAG-NAME", 400),
        (True, ".INVALID-TAG-NAME", 400),
        (
            True,
            "INVALID-TAG_NAME-BECAUSE-THIS-IS-WAY-WAY-TOO-LOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOONG",
            400,
        ),
        (False, "newtag", 404),
        (True, "generatemanifestfail", None),
        (True, "latest", 201),
        (True, "newtag", 201),
    ],
)
def test_move_tag(image_exists, test_tag, expected_status, client, app):
    with client_with_identity("devtable", client) as cl:
        test_image = "unknown"
        if image_exists:
            repo_ref = registry_model.lookup_repository("devtable", "simple")
            tag_ref = registry_model.get_repo_tag(repo_ref, "latest")
            assert tag_ref

            test_image = tag_ref.manifest.legacy_image_root_id

        params = {"repository": "devtable/simple", "tag": test_tag}
        request_body = {"image": test_image}
        if expected_status is None:
            with pytest.raises(Exception):
                conduct_api_call(cl, RepositoryTag, "put", params, request_body, expected_status)
        else:
            conduct_api_call(cl, RepositoryTag, "put", params, request_body, expected_status)


@pytest.mark.parametrize(
    "repo_namespace, repo_name, query_count",
    [
        ("devtable", "simple", 4),
        ("devtable", "history", 4),
        ("devtable", "complex", 4),
        ("devtable", "gargantuan", 4),
        ("buynlarge", "orgrepo", 6),  # +2 for permissions checks.
        ("buynlarge", "anotherorgrepo", 6),  # +2 for permissions checks.
    ],
)
def test_list_repo_tags(repo_namespace, repo_name, client, query_count, app):
    # Pre-cache media type loads to ensure consistent query count.
    Manifest.media_type.get_name(1)

    params = {"repository": repo_namespace + "/" + repo_name}
    with client_with_identity("devtable", client) as cl:
        with assert_query_count(query_count):
            tags = conduct_api_call(cl, ListRepositoryTags, "get", params).json["tags"]

        repo_ref = registry_model.lookup_repository(repo_namespace, repo_name)
        history, _ = registry_model.list_repository_tag_history(repo_ref)
        assert len(tags) == len(history)


@pytest.mark.parametrize(
    "repository, tag, expect_images",
    [
        ("devtable/simple", "prod", True),
        ("devtable/simple", "latest", True),
        ("devtable/complex", "prod", True),
    ],
)
def test_list_tag_images(repository, tag, expect_images, client, app):
    with client_with_identity("devtable", client) as cl:
        params = {"repository": repository, "tag": tag}
        result = conduct_api_call(cl, RepositoryTagImages, "get", params, None, 200).json
        assert bool(result["images"]) == expect_images
