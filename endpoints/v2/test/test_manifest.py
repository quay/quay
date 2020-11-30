import hashlib
import pytest
import time

from mock import patch

from flask import url_for
from playhouse.test_utils import count_queries

from app import instance_keys, app as realapp
from auth.auth_context_type import ValidatedAuthContext
from data import model
from data.registry_model import registry_model
from endpoints.test.shared import conduct_call
from util.security.registry_jwt import generate_bearer_token, build_context_and_subject
from test.fixtures import *


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
        "Authorization": "Bearer %s" % token.decode("ascii"),
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
