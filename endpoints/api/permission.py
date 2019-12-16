"""
Manage repository permissions.
"""

import logging

from flask import request

from endpoints.api import (
    resource,
    nickname,
    require_repo_admin,
    RepositoryParamResource,
    log_action,
    request_error,
    validate_json_request,
    path_param,
)
from endpoints.exception import NotFound
from .permission_models_pre_oci import pre_oci_model as model
from .permission_models_interface import DeleteException, SaveException

logger = logging.getLogger(__name__)


@resource("/v1/repository/<apirepopath:repository>/permissions/team/")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
class RepositoryTeamPermissionList(RepositoryParamResource):
    """
    Resource for repository team permissions.
    """

    @require_repo_admin
    @nickname("listRepoTeamPermissions")
    def get(self, namespace_name, repository_name):
        """
        List all team permission.
        """
        repo_perms = model.get_repo_permissions_by_team(namespace_name, repository_name)

        return {
            "permissions": {repo_perm.team_name: repo_perm.to_dict() for repo_perm in repo_perms}
        }


@resource("/v1/repository/<apirepopath:repository>/permissions/user/")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
class RepositoryUserPermissionList(RepositoryParamResource):
    """
    Resource for repository user permissions.
    """

    @require_repo_admin
    @nickname("listRepoUserPermissions")
    def get(self, namespace_name, repository_name):
        """
        List all user permissions.
        """
        perms = model.get_repo_permissions_by_user(namespace_name, repository_name)
        return {"permissions": {p.username: p.to_dict() for p in perms}}


@resource("/v1/repository/<apirepopath:repository>/permissions/user/<username>/transitive")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("username", "The username of the user to which the permissions apply")
class RepositoryUserTransitivePermission(RepositoryParamResource):
    """
    Resource for retrieving whether a user has access to a repository, either directly or via a
    team.
    """

    @require_repo_admin
    @nickname("getUserTransitivePermission")
    def get(self, namespace_name, repository_name, username):
        """
        Get the fetch the permission for the specified user.
        """

        roles = model.get_repo_roles(username, namespace_name, repository_name)

        if not roles:
            raise NotFound

        return {"permissions": [r.to_dict() for r in roles]}


@resource("/v1/repository/<apirepopath:repository>/permissions/user/<username>")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("username", "The username of the user to which the permission applies")
class RepositoryUserPermission(RepositoryParamResource):
    """
    Resource for managing individual user permissions.
    """

    schemas = {
        "UserPermission": {
            "type": "object",
            "description": "Description of a user permission.",
            "required": ["role",],
            "properties": {
                "role": {
                    "type": "string",
                    "description": "Role to use for the user",
                    "enum": ["read", "write", "admin",],
                },
            },
        },
    }

    @require_repo_admin
    @nickname("getUserPermissions")
    def get(self, namespace_name, repository_name, username):
        """
        Get the permission for the specified user.
        """
        logger.debug(
            "Get repo: %s/%s permissions for user %s", namespace_name, repository_name, username
        )
        perm = model.get_repo_permission_for_user(username, namespace_name, repository_name)
        return perm.to_dict()

    @require_repo_admin
    @nickname("changeUserPermissions")
    @validate_json_request("UserPermission")
    def put(self, namespace_name, repository_name, username):  # Also needs to respond to post
        """
        Update the perimssions for an existing repository.
        """
        new_permission = request.get_json()

        logger.debug("Setting permission to: %s for user %s", new_permission["role"], username)

        try:
            perm = model.set_repo_permission_for_user(
                username, namespace_name, repository_name, new_permission["role"]
            )
            resp = perm.to_dict()
        except SaveException as ex:
            raise request_error(exception=ex)

        log_action(
            "change_repo_permission",
            namespace_name,
            {
                "username": username,
                "repo": repository_name,
                "namespace": namespace_name,
                "role": new_permission["role"],
            },
            repo_name=repository_name,
        )

        return resp, 200

    @require_repo_admin
    @nickname("deleteUserPermissions")
    def delete(self, namespace_name, repository_name, username):
        """
        Delete the permission for the user.
        """
        try:
            model.delete_repo_permission_for_user(username, namespace_name, repository_name)
        except DeleteException as ex:
            raise request_error(exception=ex)

        log_action(
            "delete_repo_permission",
            namespace_name,
            {"username": username, "repo": repository_name, "namespace": namespace_name},
            repo_name=repository_name,
        )

        return "", 204


@resource("/v1/repository/<apirepopath:repository>/permissions/team/<teamname>")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("teamname", "The name of the team to which the permission applies")
class RepositoryTeamPermission(RepositoryParamResource):
    """
    Resource for managing individual team permissions.
    """

    schemas = {
        "TeamPermission": {
            "type": "object",
            "description": "Description of a team permission.",
            "required": ["role",],
            "properties": {
                "role": {
                    "type": "string",
                    "description": "Role to use for the team",
                    "enum": ["read", "write", "admin",],
                },
            },
        },
    }

    @require_repo_admin
    @nickname("getTeamPermissions")
    def get(self, namespace_name, repository_name, teamname):
        """
        Fetch the permission for the specified team.
        """
        logger.debug(
            "Get repo: %s/%s permissions for team %s", namespace_name, repository_name, teamname
        )
        role = model.get_repo_role_for_team(teamname, namespace_name, repository_name)
        return role.to_dict()

    @require_repo_admin
    @nickname("changeTeamPermissions")
    @validate_json_request("TeamPermission")
    def put(self, namespace_name, repository_name, teamname):
        """
        Update the existing team permission.
        """
        new_permission = request.get_json()

        logger.debug("Setting permission to: %s for team %s", new_permission["role"], teamname)

        try:
            perm = model.set_repo_permission_for_team(
                teamname, namespace_name, repository_name, new_permission["role"]
            )
            resp = perm.to_dict()
        except SaveException as ex:
            raise request_error(exception=ex)

        log_action(
            "change_repo_permission",
            namespace_name,
            {"team": teamname, "repo": repository_name, "role": new_permission["role"]},
            repo_name=repository_name,
        )
        return resp, 200

    @require_repo_admin
    @nickname("deleteTeamPermissions")
    def delete(self, namespace_name, repository_name, teamname):
        """
        Delete the permission for the specified team.
        """
        try:
            model.delete_repo_permission_for_team(teamname, namespace_name, repository_name)
        except DeleteException as ex:
            raise request_error(exception=ex)

        log_action(
            "delete_repo_permission",
            namespace_name,
            {"team": teamname, "repo": repository_name},
            repo_name=repository_name,
        )

        return "", 204
