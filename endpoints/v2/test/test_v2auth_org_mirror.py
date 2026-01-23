# -*- coding: utf-8 -*-
"""
Unit tests for v2auth handling of ORG_MIRROR repository state.

Tests that org-level mirrored repositories properly authorize
push access for the mirroring robot only.
"""

import pytest
from flask import url_for

from app import app as original_app
from app import instance_keys
from data import model
from data.database import (
    OrgMirrorConfig,
    OrgMirrorRepository,
    OrgMirrorRepoStatus,
    Repository,
    RepositoryState,
    SourceRegistryType,
    Visibility,
)
from data.model.user import create_robot, get_robot_and_metadata, get_user
from endpoints.test.shared import conduct_call, gen_basic_auth
from test.fixtures import *
from util.security.registry_jwt import decode_bearer_token


def get_robot_password(username):
    """Get the password for a robot account."""
    parent_name, robot_shortname = username.split("+", 1)
    parent = get_user(parent_name)
    _, token, _ = get_robot_and_metadata(robot_shortname, parent)
    return token


def _create_org_mirror_repo(org_name, repo_name, robot):
    """Create a repository with ORG_MIRROR state and associated OrgMirrorConfig."""
    from datetime import datetime

    from data.database import OrgMirrorStatus

    org = get_user(org_name)
    visibility = Visibility.get(name="private")

    # Get or create repo
    repo = model.repository.get_repository(org_name, repo_name)
    if repo is None:
        repo = model.repository.create_repository(org_name, repo_name, robot, visibility="private")
        repo = Repository.get(Repository.id == repo.id)

    # Set state to ORG_MIRROR
    repo.state = RepositoryState.ORG_MIRROR
    repo.save()

    # Create OrgMirrorConfig if it doesn't exist
    try:
        config = OrgMirrorConfig.get(OrgMirrorConfig.organization == org)
    except OrgMirrorConfig.DoesNotExist:
        config = OrgMirrorConfig.create(
            organization=org,
            is_enabled=True,
            external_registry_type=SourceRegistryType.QUAY,
            external_registry_url="https://registry.example.com",
            external_namespace="source-namespace",
            internal_robot=robot,
            visibility=visibility,
            sync_interval=3600,
            sync_start_date=datetime.utcnow(),
            sync_status=OrgMirrorStatus.NEVER_RUN,
            sync_retries_remaining=3,
            skopeo_timeout=300,
        )

    # Create OrgMirrorRepository entry
    try:
        org_mirror_repo = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == repo_name)
        )
    except OrgMirrorRepository.DoesNotExist:
        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name=repo_name,
            repository=repo,
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )

    return repo, config, org_mirror_repo


class TestV2AuthOrgMirror:
    """Tests for v2auth handling of ORG_MIRROR repository state."""

    def test_org_mirror_robot_can_push(self, app, client):
        """
        The robot assigned to the org mirror config should be able to push
        to ORG_MIRROR state repositories.
        """
        # Get existing robot for devtable
        devtable = get_user("devtable")
        robot, _ = create_robot("orgmirrorbot", devtable)

        # Create org mirror repo
        _repo, _config, _org_mirror_repo = _create_org_mirror_repo("devtable", "orgmirrored", robot)

        # Request push scope as the robot
        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:devtable/orgmirrored:pull,push",
        }

        robot_password = get_robot_password(robot.username)
        headers = {"Authorization": gen_basic_auth(robot.username, robot_password)}

        resp = conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
            headers=headers,
        )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        # Robot should have push access
        assert len(decoded["access"]) == 1
        access = decoded["access"][0]
        assert "push" in access["actions"]
        assert "pull" in access["actions"]

    def test_org_mirror_non_robot_cannot_push(self, app, client):
        """
        Non-robot users should not be able to push to ORG_MIRROR state repositories,
        even if they are the owner.
        """
        # Get existing robot for devtable
        devtable = get_user("devtable")
        robot, _ = create_robot("orgmirrorbot2", devtable)

        # Create org mirror repo
        _repo, _config, _org_mirror_repo = _create_org_mirror_repo(
            "devtable", "orgmirrored2", robot
        )

        # Request push scope as devtable (owner, but not the robot)
        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:devtable/orgmirrored2:pull,push,*",
        }

        headers = {"Authorization": gen_basic_auth("devtable", "password")}

        resp = conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
            headers=headers,
        )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        # User should only have pull access (no push)
        assert len(decoded["access"]) == 1
        access = decoded["access"][0]
        assert "push" not in access["actions"]
        assert "pull" in access["actions"]

    def test_org_mirror_wrong_robot_cannot_push(self, app, client):
        """
        A different robot (not the one assigned to the org mirror config)
        should not be able to push to ORG_MIRROR state repositories.
        """
        # Get existing robot for devtable
        devtable = get_user("devtable")
        mirror_robot, _ = create_robot("orgmirrorbot3", devtable)
        other_robot, _ = create_robot("otherrobot", devtable)

        # Create org mirror repo with mirror_robot
        _repo, _config, _org_mirror_repo = _create_org_mirror_repo(
            "devtable", "orgmirrored3", mirror_robot
        )

        # Request push scope as the OTHER robot
        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:devtable/orgmirrored3:pull,push",
        }

        other_robot_password = get_robot_password(other_robot.username)
        headers = {"Authorization": gen_basic_auth(other_robot.username, other_robot_password)}

        resp = conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
            headers=headers,
        )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        # Other robot should not have push access
        assert len(decoded["access"]) == 1
        access = decoded["access"][0]
        assert "push" not in access["actions"]

    def test_org_mirror_anonymous_can_pull_public(self, app, client):
        """
        Anonymous users should be able to pull from public ORG_MIRROR repositories.
        """
        # Get public org
        public_user = get_user("public")
        robot, _ = create_robot("publicorgmirrorbot", public_user)

        # Create org mirror repo with public visibility
        repo, _config, _org_mirror_repo = _create_org_mirror_repo(
            "public", "publicorgmirrored", robot
        )

        # Make repo public
        model.repository.set_repository_visibility(repo, "public")

        # Request pull scope anonymously
        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:public/publicorgmirrored:pull",
        }

        resp = conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
        )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        # Anonymous should have pull access
        assert len(decoded["access"]) == 1
        access = decoded["access"][0]
        assert "pull" in access["actions"]
        assert "push" not in access["actions"]

    def test_org_mirror_admin_action_denied(self, app, client):
        """
        Admin actions (*) should be denied for ORG_MIRROR state repositories.
        """
        # Get existing robot for devtable
        devtable = get_user("devtable")
        robot, _ = create_robot("orgmirrorbot4", devtable)

        # Create org mirror repo
        _repo, _config, _org_mirror_repo = _create_org_mirror_repo(
            "devtable", "orgmirrored4", robot
        )

        # Request admin scope as devtable
        params = {
            "service": original_app.config["SERVER_HOSTNAME"],
            "scope": "repository:devtable/orgmirrored4:pull,push,*",
        }

        headers = {"Authorization": gen_basic_auth("devtable", "password")}

        resp = conduct_call(
            client,
            "v2.generate_registry_jwt",
            url_for,
            "GET",
            params,
            {},
            200,
            headers=headers,
        )

        token = resp.json["token"]
        decoded = decode_bearer_token(token, instance_keys, original_app.config)

        # User should not have admin access
        assert len(decoded["access"]) == 1
        access = decoded["access"][0]
        assert "*" not in access["actions"]
