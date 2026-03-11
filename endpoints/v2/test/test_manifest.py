import hashlib
import json
import time
from unittest.mock import Mock, patch

from flask import url_for
from playhouse.test_utils import count_queries

from app import app as realapp
from app import instance_keys
from auth.auth_context_type import ValidatedAuthContext
from data import model
from data.model.oci.tag import set_tag_immutable
from data.registry_model import registry_model
from endpoints.test.shared import conduct_call, toggle_feature
from image.docker.schema2.test.test_config import (
    CONFIG_BYTES,
    CONFIG_DIGEST,
    CONFIG_SIZE,
)
from test.fixtures import *  # noqa: F401, F403
from util.security.registry_jwt import build_context_and_subject, generate_bearer_token


def test_e2e_query_count_manifest_norewrite(client, app):
    repo_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repo_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    params = {
        "repository": "devtable/simple",
        "manifest_ref": manifest.digest,
    }

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
        "Authorization": "Bearer %s" % token,
    }

    # Conduct a call to prime the instance key and other caches.
    conduct_call(
        client,
        "v2.write_manifest_by_digest",
        url_for,
        "PUT",
        params,
        expected_code=201,
        headers=headers,
        raw_body=manifest.internal_manifest_bytes.as_encoded_str(),
    )

    timecode = time.time()

    def get_time():
        return timecode + 10

    with patch("time.time", get_time):
        # Necessary in order to have the tag updates not occur in the same second, which is the
        # granularity supported currently.
        with count_queries() as counter:
            conduct_call(
                client,
                "v2.write_manifest_by_digest",
                url_for,
                "PUT",
                params,
                expected_code=201,
                headers=headers,
                raw_body=manifest.internal_manifest_bytes.as_encoded_str(),
            )

        assert counter.count <= 27


INVALID_DOCKER_V2_MANIFEST = json.dumps(
    {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        "config": {
            "mediaType": "application/vnd.docker.container.image.v1+json",
            "size": CONFIG_SIZE,
            "digest": CONFIG_DIGEST,
        },
        "layers": [
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 1234,
                "digest": "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736",
            },
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 32654,
                "digest": "sha256:e692418e4cbaf90ca69d05a66403747baa33ee08806650b51fab815ad7fc331f",
            },
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": -1,
                "digest": "sha256:3c3a4604a545cdc127456d94e421cd355bca5b528f4a9c1905b15da2eb4a4c6b",
            },
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 73109,
                "digest": "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736",
            },
        ],
    }
).encode("utf-8")


def test_push_malformed_manifest_docker_v2s2(client, app):
    repo_ref = registry_model.lookup_repository("devtable", "simple")

    params = {
        "repository": "devtable/simple",
        "manifest_ref": "sha256:" + hashlib.sha256(INVALID_DOCKER_V2_MANIFEST).hexdigest(),
    }

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
        "Authorization": "Bearer %s" % token,
    }

    # Conduct a call to prime the instance key and other caches.
    conduct_call(
        client,
        "v2.write_manifest_by_digest",
        url_for,
        "PUT",
        params,
        expected_code=400,
        headers=headers,
        raw_body=INVALID_DOCKER_V2_MANIFEST,
    )


INVALID_OCI_MANIFEST = json.dumps(
    {
        "schemaVersion": 2,
        "config": {
            "mediaType": "application/vnd.oci.image.config.v1+json",
            "size": 7023,
            "digest": "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7",
        },
        "layers": [
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "size": 32654,
                "digest": "sha256:9834876dcfb05cb167a5c24953eba58c4ac89b1adf57f28f2f9d09af107ee8f0",
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "size": -1,
                "digest": "sha256:3c3a4604a545cdc127456d94e421cd355bca5b528f4a9c1905b15da2eb4a4c6b",
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "size": 73109,
                "digest": "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736",
            },
        ],
        "annotations": {"com.example.key1": "value1", "com.example.key2": "value2"},
    }
).encode("utf-8")


def test_push_malformed_manifest_oci_manifest(client, app):
    repo_ref = registry_model.lookup_repository("devtable", "simple")

    params = {
        "repository": "devtable/simple",
        "manifest_ref": "sha256:" + hashlib.sha256(INVALID_OCI_MANIFEST).hexdigest(),
    }

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
        "Authorization": "Bearer %s" % token,
    }

    # Conduct a call to prime the instance key and other caches.
    conduct_call(
        client,
        "v2.write_manifest_by_digest",
        url_for,
        "PUT",
        params,
        expected_code=400,
        headers=headers,
        raw_body=INVALID_OCI_MANIFEST,
    )


def test_fetch_manifest_by_digest_tracks_pull_metrics(client, app):
    """
    Test that fetching a manifest by digest calls the pull metrics tracking.

    This test verifies that PROJQUAY-9877 is fixed: "Last Pulled" and "Pull Count"
    should update when image is pulled by digest, not just by tag.
    """
    repo_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repo_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    params = {
        "repository": "devtable/simple",
        "manifest_ref": manifest.digest,
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
        "Authorization": "Bearer %s" % token,
    }

    # Mock the pullmetrics module to verify track_manifest_pull is called
    with patch("endpoints.v2.manifest.pullmetrics") as mock_pullmetrics:
        # Setup mock
        mock_event = Mock()
        mock_pullmetrics.get_event.return_value = mock_event

        # Fetch manifest by digest
        conduct_call(
            client,
            "v2.fetch_manifest_by_digest",
            url_for,
            "GET",
            params,
            expected_code=200,
            headers=headers,
        )

        # Verify that get_event was called and track_manifest_pull was invoked
        mock_pullmetrics.get_event.assert_called_once()
        mock_event.track_manifest_pull.assert_called_once()

        # Verify the call arguments
        call_args = mock_event.track_manifest_pull.call_args
        # First positional arg is repository_ref, second is manifest_digest
        assert call_args[0][1] == manifest.digest


def test_fetch_manifest_by_tagname_tracks_pull_metrics(client, app):
    """
    Test that fetching a manifest by tag name calls the pull metrics tracking.

    This is a companion test to ensure tag-based pulls are also tracked correctly.
    """
    params = {
        "repository": "devtable/simple",
        "manifest_ref": "latest",
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
        "Authorization": "Bearer %s" % token,
    }

    # Mock the pullmetrics module to verify track_tag_pull is called
    with patch("endpoints.v2.manifest.pullmetrics") as mock_pullmetrics:
        # Setup mock
        mock_event = Mock()
        mock_pullmetrics.get_event.return_value = mock_event

        # Fetch manifest by tag name
        conduct_call(
            client,
            "v2.fetch_manifest_by_tagname",
            url_for,
            "GET",
            params,
            expected_code=200,
            headers=headers,
        )

        # Verify that get_event was called and track_tag_pull was invoked
        mock_pullmetrics.get_event.assert_called_once()
        mock_event.track_tag_pull.assert_called_once()

        # Verify the call arguments
        call_args = mock_event.track_tag_pull.call_args
        # Args: repository_ref, tag_name, manifest_digest
        assert call_args[0][1] == "latest"  # tag_name


def test_delete_manifest_by_tag_immutable_returns_409(client, app):
    """Test that DELETE on an immutable tag returns 409 with TAG_IMMUTABLE error."""
    with toggle_feature("IMMUTABLE_TAGS", True):
        repo_ref = registry_model.lookup_repository("devtable", "simple")

        # Make the tag immutable
        set_tag_immutable(repo_ref.id, "latest", True)

        params = {
            "repository": "devtable/simple",
            "manifest_ref": "latest",
        }

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
            "Authorization": "Bearer %s" % token,
        }

        rv = conduct_call(
            client,
            "v2.delete_manifest_by_tag",
            url_for,
            "DELETE",
            params,
            expected_code=409,
            headers=headers,
        )

        # Verify TAG_IMMUTABLE error in response
        response_data = json.loads(rv.data)
        assert "errors" in response_data
        assert response_data["errors"][0]["code"] == "TAG_IMMUTABLE"


def test_delete_manifest_by_digest_immutable_returns_409(client, app):
    """Test that DELETE manifest by digest returns 409 when any tag is immutable."""
    with toggle_feature("IMMUTABLE_TAGS", True):
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)

        # Make the tag immutable
        set_tag_immutable(repo_ref.id, "latest", True)

        params = {
            "repository": "devtable/simple",
            "manifest_ref": manifest.digest,
        }

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
            "Authorization": "Bearer %s" % token,
        }

        rv = conduct_call(
            client,
            "v2.delete_manifest_by_digest",
            url_for,
            "DELETE",
            params,
            expected_code=409,
            headers=headers,
        )

        # Verify TAG_IMMUTABLE error in response
        response_data = json.loads(rv.data)
        assert "errors" in response_data
        assert len(response_data["errors"]) == 1

        error = response_data["errors"][0]
        assert error["code"] == "TAG_IMMUTABLE"
        assert "immutable" in error["message"].lower()
        assert "detail" in error
        assert "latest" in error["detail"]["message"]


def test_write_manifest_by_tagname_immutable_returns_409(client, app):
    """Test that PUT manifest on an immutable tag returns 409 with TAG_IMMUTABLE error."""
    with toggle_feature("IMMUTABLE_TAGS", True):
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)

        # Make the tag immutable
        set_tag_immutable(repo_ref.id, "latest", True)

        params = {
            "repository": "devtable/simple",
            "manifest_ref": "latest",
        }

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
            "Authorization": "Bearer %s" % token,
        }

        rv = conduct_call(
            client,
            "v2.write_manifest_by_tagname",
            url_for,
            "PUT",
            params,
            expected_code=409,
            headers=headers,
            raw_body=manifest.internal_manifest_bytes.as_encoded_str(),
        )

        # Verify TAG_IMMUTABLE error in response
        response_data = json.loads(rv.data)
        assert "errors" in response_data
        assert len(response_data["errors"]) == 1

        error = response_data["errors"][0]
        assert error["code"] == "TAG_IMMUTABLE"
        assert "immutable" in error["message"].lower()
        assert "detail" in error
        assert "latest" in error["detail"]["message"]
