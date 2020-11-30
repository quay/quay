"""
Manage repository access tokens (DEPRECATED).
"""

import logging

from endpoints.api import (
    resource,
    nickname,
    require_repo_admin,
    RepositoryParamResource,
    validate_json_request,
    path_param,
)

logger = logging.getLogger(__name__)


@resource("/v1/repository/<apirepopath:repository>/tokens/")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
class RepositoryTokenList(RepositoryParamResource):
    """
    Resource for creating and listing repository tokens.
    """

    schemas = {
        "NewToken": {
            "type": "object",
            "description": "Description of a new token.",
            "required": [
                "friendlyName",
            ],
            "properties": {
                "friendlyName": {
                    "type": "string",
                    "description": "Friendly name to help identify the token",
                },
            },
        },
    }

    @require_repo_admin
    @nickname("listRepoTokens")
    def get(self, namespace_name, repo_name):
        """
        List the tokens for the specified repository.
        """
        return {
            "message": "Handling of access tokens is no longer supported",
        }, 410

    @require_repo_admin
    @nickname("createToken")
    @validate_json_request("NewToken")
    def post(self, namespace_name, repo_name):
        """
        Create a new repository token.
        """
        return {
            "message": "Creation of access tokens is no longer supported",
        }, 410


@resource("/v1/repository/<apirepopath:repository>/tokens/<code>")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("code", "The token code")
class RepositoryToken(RepositoryParamResource):
    """
    Resource for managing individual tokens.
    """

    schemas = {
        "TokenPermission": {
            "type": "object",
            "description": "Description of a token permission",
            "required": [
                "role",
            ],
            "properties": {
                "role": {
                    "type": "string",
                    "description": "Role to use for the token",
                    "enum": [
                        "read",
                        "write",
                        "admin",
                    ],
                },
            },
        },
    }

    @require_repo_admin
    @nickname("getTokens")
    def get(self, namespace_name, repo_name, code):
        """
        Fetch the specified repository token information.
        """
        return {
            "message": "Handling of access tokens is no longer supported",
        }, 410

    @require_repo_admin
    @nickname("changeToken")
    @validate_json_request("TokenPermission")
    def put(self, namespace_name, repo_name, code):
        """
        Update the permissions for the specified repository token.
        """
        return {
            "message": "Handling of access tokens is no longer supported",
        }, 410

    @require_repo_admin
    @nickname("deleteToken")
    def delete(self, namespace_name, repo_name, code):
        """
        Delete the repository token.
        """
        return {
            "message": "Handling of access tokens is no longer supported",
        }, 410
