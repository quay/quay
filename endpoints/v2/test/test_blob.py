import hashlib
import pytest

from mock import patch
from flask import url_for
from playhouse.test_utils import assert_query_count

from app import instance_keys, app as realapp
from auth.auth_context_type import ValidatedAuthContext
from data import model
from data.cache import InMemoryDataModelCache
from data.cache.test.test_cache import TEST_CACHE_CONFIG
from data.database import ImageStorageLocation
from endpoints.test.shared import conduct_call
from util.security.registry_jwt import generate_bearer_token, build_context_and_subject
from test.fixtures import *


@pytest.mark.parametrize(
    "method, endpoint",
    [
        ("GET", "download_blob"),
        ("HEAD", "check_blob_exists"),
    ],
)
def test_blob_caching(method, endpoint, client, app):
    digest = "sha256:" + hashlib.sha256(b"a").hexdigest()
    location = ImageStorageLocation.get(name="local_us")
    model.blob.store_blob_record_and_temp_link("devtable", "simple", digest, location, 1, 10000000)

    params = {
        "repository": "devtable/simple",
        "digest": digest,
    }

    user = model.user.get_user("devtable")
    access = [
        {
            "type": "repository",
            "name": "devtable/simple",
            "actions": ["pull"],
        }
    ]

    context, subject = build_context_and_subject(ValidatedAuthContext(user=user))
    token = generate_bearer_token(
        realapp.config["SERVER_HOSTNAME"], subject, context, access, 600, instance_keys
    )

    headers = {
        "Authorization": "Bearer %s" % token.decode("ascii"),
    }

    # Run without caching to make sure the request works. This also preloads some of
    # our global model caches.
    conduct_call(
        client, "v2." + endpoint, url_for, method, params, expected_code=200, headers=headers
    )

    with patch("endpoints.v2.blob.model_cache", InMemoryDataModelCache(TEST_CACHE_CONFIG)):
        # First request should make a DB query to retrieve the blob.
        conduct_call(
            client, "v2." + endpoint, url_for, method, params, expected_code=200, headers=headers
        )

        # Subsequent requests should use the cached blob.
        with assert_query_count(0):
            conduct_call(
                client,
                "v2." + endpoint,
                url_for,
                method,
                params,
                expected_code=200,
                headers=headers,
            )


@pytest.mark.parametrize(
    "mount_digest, source_repo, username, expect_success",
    [
        # Unknown blob.
        ("sha256:unknown", "devtable/simple", "devtable", False),
        # Blob not in repo.
        ("sha256:" + hashlib.sha256(b"a").hexdigest(), "devtable/complex", "devtable", False),
        # Blob in repo.
        ("sha256:" + hashlib.sha256(b"b").hexdigest(), "devtable/complex", "devtable", True),
        # No access to repo.
        ("sha256:" + hashlib.sha256(b"b").hexdigest(), "devtable/complex", "public", False),
        # Public repo.
        ("sha256:" + hashlib.sha256(b"c").hexdigest(), "public/publicrepo", "devtable", True),
    ],
)
def test_blob_mounting(mount_digest, source_repo, username, expect_success, client, app):
    location = ImageStorageLocation.get(name="local_us")

    # Store and link some blobs.
    digest = "sha256:" + hashlib.sha256(b"a").hexdigest()
    model.blob.store_blob_record_and_temp_link("devtable", "simple", digest, location, 1, 10000000)

    digest = "sha256:" + hashlib.sha256(b"b").hexdigest()
    model.blob.store_blob_record_and_temp_link("devtable", "complex", digest, location, 1, 10000000)

    digest = "sha256:" + hashlib.sha256(b"c").hexdigest()
    model.blob.store_blob_record_and_temp_link(
        "public", "publicrepo", digest, location, 1, 10000000
    )

    params = {
        "repository": "devtable/building",
        "mount": mount_digest,
        "from": source_repo,
    }

    user = model.user.get_user(username)
    access = [
        {
            "type": "repository",
            "name": "devtable/building",
            "actions": ["pull", "push"],
        }
    ]

    if source_repo.find(username) == 0:
        access.append(
            {
                "type": "repository",
                "name": source_repo,
                "actions": ["pull"],
            }
        )

    context, subject = build_context_and_subject(ValidatedAuthContext(user=user))
    token = generate_bearer_token(
        realapp.config["SERVER_HOSTNAME"], subject, context, access, 600, instance_keys
    )

    headers = {
        "Authorization": "Bearer %s" % token.decode("ascii"),
    }

    expected_code = 201 if expect_success else 202
    conduct_call(
        client,
        "v2.start_blob_upload",
        url_for,
        "POST",
        params,
        expected_code=expected_code,
        headers=headers,
    )

    repository = model.repository.get_repository("devtable", "building")

    if expect_success:
        # Ensure the blob now exists under the repo.
        assert model.oci.blob.get_repository_blob_by_digest(repository, mount_digest)
    else:
        assert model.oci.blob.get_repository_blob_by_digest(repository, mount_digest) is None


def test_blob_upload_offset(client, app):
    user = model.user.get_user("devtable")
    access = [
        {
            "type": "repository",
            "name": "devtable/simple",
            "actions": ["pull", "push"],
        }
    ]

    context, subject = build_context_and_subject(ValidatedAuthContext(user=user))
    token = generate_bearer_token(
        realapp.config["SERVER_HOSTNAME"], subject, context, access, 600, instance_keys
    )

    headers = {
        "Authorization": "Bearer %s" % token.decode("ascii"),
    }

    # Create a blob upload request.
    params = {
        "repository": "devtable/simple",
    }
    response = conduct_call(
        client, "v2.start_blob_upload", url_for, "POST", params, expected_code=202, headers=headers
    )

    upload_uuid = response.headers["Docker-Upload-UUID"]

    # Attempt to start an upload past index zero.
    params = {
        "repository": "devtable/simple",
        "upload_uuid": upload_uuid,
    }

    headers = {
        "Authorization": "Bearer %s" % token.decode("ascii"),
        "Content-Range": "13-50",
    }

    conduct_call(
        client,
        "v2.upload_chunk",
        url_for,
        "PATCH",
        params,
        expected_code=416,
        headers=headers,
        body="something",
    )
