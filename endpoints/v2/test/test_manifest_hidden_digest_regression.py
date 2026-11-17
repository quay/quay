"""Regression for digest deletion of a manifest protected only by hidden tags."""

import json

import pytest
from flask import url_for

from app import app as realapp
from app import instance_keys
from auth.auth_context_type import ValidatedAuthContext
from data import model
from data.database import Tag
from data.model.oci.tag import filter_to_alive_tags, set_tag_immutable
from data.registry_model import registry_model
from endpoints.test.shared import conduct_call, toggle_feature
from test.fixtures import *  # noqa: F401, F403
from util.security.registry_jwt import build_context_and_subject, generate_bearer_token


@pytest.mark.parametrize("hidden", [False, True], ids=["visible", "hidden"])
@pytest.mark.parametrize("immutable", [False, True], ids=["mutable", "immutable"])
def test_digest_delete_hidden_tag_regression(client, app, hidden, immutable):
    """Digest deletion includes hidden tags but preserves immutable-tag protection."""
    with toggle_feature("IMMUTABLE_TAGS", True):
        repository = registry_model.lookup_repository("devtable", "simple")
        tag = registry_model.get_repo_tag(repository, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)
        if immutable:
            set_tag_immutable(repository.id, "latest", True)
        Tag.update(hidden=hidden).where(Tag.manifest == manifest._db_id).execute()

        def alive():
            return filter_to_alive_tags(
                Tag.select().where(Tag.manifest == manifest._db_id), allow_hidden=True
            ).count()

        assert alive() > 0

        user = model.user.get_user("devtable")
        context, subject = build_context_and_subject(ValidatedAuthContext(user=user))
        token = generate_bearer_token(
            realapp.config["SERVER_HOSTNAME"],
            subject,
            context,
            [
                {
                    "type": "repository",
                    "name": "devtable/simple",
                    "actions": ["pull", "push"],
                }
            ],
            600,
            instance_keys,
        )
        response = conduct_call(
            client,
            "v2.delete_manifest_by_digest",
            url_for,
            "DELETE",
            {"repository": "devtable/simple", "manifest_ref": manifest.digest},
            expected_code=409 if immutable else 202,
            headers={"Authorization": "Bearer " + token},
        )
        if immutable:
            assert json.loads(response.data)["errors"][0]["code"] == "TAG_IMMUTABLE"
            assert alive() > 0
        else:
            assert alive() == 0
