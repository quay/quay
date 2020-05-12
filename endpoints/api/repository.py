"""
List, create and manage repositories.
"""

import logging
import datetime
import features

from collections import defaultdict
from datetime import timedelta, datetime

from flask import request, abort

from app import dockerfile_build_queue, tuf_metadata_api, repository_gc_queue
from data.database import RepositoryState
from endpoints.api import (
    format_date,
    nickname,
    log_action,
    validate_json_request,
    require_repo_read,
    require_repo_write,
    require_repo_admin,
    RepositoryParamResource,
    resource,
    parse_args,
    ApiResource,
    request_error,
    require_scope,
    path_param,
    page_support,
    query_param,
    show_if,
)
from endpoints.api.repository_models_pre_oci import pre_oci_model as model
from endpoints.exception import (
    Unauthorized,
    NotFound,
    InvalidRequest,
    ExceedsLicenseException,
    DownstreamIssue,
)
from endpoints.api.billing import lookup_allowed_private_repos, get_namespace_plan
from endpoints.api.subscribe import check_repository_usage

from auth.permissions import (
    ModifyRepositoryPermission,
    AdministerRepositoryPermission,
    CreateRepositoryPermission,
    ReadRepositoryPermission,
)
from auth.auth_context import get_authenticated_user
from auth import scopes
from util.names import REPOSITORY_NAME_REGEX
from util.parsing import truthy_bool

logger = logging.getLogger(__name__)

MAX_DAYS_IN_3_MONTHS = 92


def check_allowed_private_repos(namespace):
    """
    Checks to see if the given namespace has reached its private repository limit.

    If so, raises a ExceedsLicenseException.
    """
    # Not enabled if billing is disabled.
    if not features.BILLING:
        return

    if not lookup_allowed_private_repos(namespace):
        raise ExceedsLicenseException()


@resource("/v1/repository")
class RepositoryList(ApiResource):
    """
    Operations for creating and listing repositories.
    """

    schemas = {
        "NewRepo": {
            "type": "object",
            "description": "Description of a new repository",
            "required": ["repository", "visibility", "description",],
            "properties": {
                "repository": {"type": "string", "description": "Repository name",},
                "visibility": {
                    "type": "string",
                    "description": "Visibility which the repository will start with",
                    "enum": ["public", "private",],
                },
                "namespace": {
                    "type": "string",
                    "description": (
                        "Namespace in which the repository should be created. If omitted, the "
                        "username of the caller is used"
                    ),
                },
                "description": {
                    "type": "string",
                    "description": "Markdown encoded description for the repository",
                },
                "repo_kind": {
                    "type": ["string", "null"],
                    "description": "The kind of repository",
                    "enum": ["image", "application", None],
                },
            },
        },
    }

    @require_scope(scopes.CREATE_REPO)
    @nickname("createRepo")
    @validate_json_request("NewRepo")
    def post(self):
        """
        Create a new repository.
        """
        owner = get_authenticated_user()
        req = request.get_json()

        if owner is None and "namespace" not in "req":
            raise InvalidRequest("Must provide a namespace or must be logged in.")

        namespace_name = req["namespace"] if "namespace" in req else owner.username

        permission = CreateRepositoryPermission(namespace_name)
        if permission.can():
            repository_name = req["repository"]
            visibility = req["visibility"]

            if model.repo_exists(namespace_name, repository_name):
                raise request_error(message="Repository already exists")

            visibility = req["visibility"]
            if visibility == "private":
                check_allowed_private_repos(namespace_name)

            # Verify that the repository name is valid.
            if not REPOSITORY_NAME_REGEX.match(repository_name):
                raise InvalidRequest("Invalid repository name")

            kind = req.get("repo_kind", "image") or "image"
            created = model.create_repo(
                namespace_name,
                repository_name,
                owner,
                req["description"],
                visibility=visibility,
                repo_kind=kind,
            )
            if created is None:
                raise InvalidRequest("Could not create repository")

            log_action(
                "create_repo",
                namespace_name,
                {"repo": repository_name, "namespace": namespace_name},
                repo_name=repository_name,
            )
            return {"namespace": namespace_name, "name": repository_name, "kind": kind,}, 201

        raise Unauthorized()

    @require_scope(scopes.READ_REPO)
    @nickname("listRepos")
    @parse_args()
    @query_param("namespace", "Filters the repositories returned to this namespace", type=str)
    @query_param(
        "starred",
        "Filters the repositories returned to those starred by the user",
        type=truthy_bool,
        default=False,
    )
    @query_param(
        "public",
        "Adds any repositories visible to the user by virtue of being public",
        type=truthy_bool,
        default=False,
    )
    @query_param(
        "last_modified",
        "Whether to include when the repository was last modified.",
        type=truthy_bool,
        default=False,
    )
    @query_param(
        "popularity",
        "Whether to include the repository's popularity metric.",
        type=truthy_bool,
        default=False,
    )
    @query_param("repo_kind", "The kind of repositories to return", type=str, default="image")
    @page_support()
    def get(self, page_token, parsed_args):
        """
        Fetch the list of repositories visible to the current user under a variety of situations.
        """
        # Ensure that the user requests either filtered by a namespace, only starred repositories,
        # or public repositories. This ensures that the user is not requesting *all* visible repos,
        # which can cause a surge in DB CPU usage.
        if (
            not parsed_args["namespace"]
            and not parsed_args["starred"]
            and not parsed_args["public"]
        ):
            raise InvalidRequest("namespace, starred or public are required for this API call")

        user = get_authenticated_user()
        username = user.username if user else None
        last_modified = parsed_args["last_modified"]
        popularity = parsed_args["popularity"]

        if parsed_args["starred"] and not username:
            # No repositories should be returned, as there is no user.
            abort(400)

        repos, next_page_token = model.get_repo_list(
            parsed_args["starred"],
            user,
            parsed_args["repo_kind"],
            parsed_args["namespace"],
            username,
            parsed_args["public"],
            page_token,
            last_modified,
            popularity,
        )

        return {"repositories": [repo.to_dict() for repo in repos]}, next_page_token


@resource("/v1/repository/<apirepopath:repository>")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
class Repository(RepositoryParamResource):
    """
    Operations for managing a specific repository.
    """

    schemas = {
        "RepoUpdate": {
            "type": "object",
            "description": "Fields which can be updated in a repository.",
            "required": ["description",],
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Markdown encoded description for the repository",
                },
            },
        }
    }

    @parse_args()
    @query_param(
        "includeStats", "Whether to include action statistics", type=truthy_bool, default=False
    )
    @query_param(
        "includeTags", "Whether to include repository tags", type=truthy_bool, default=True
    )
    @require_repo_read
    @nickname("getRepo")
    def get(self, namespace, repository, parsed_args):
        """
        Fetch the specified repository.
        """
        logger.debug("Get repo: %s/%s" % (namespace, repository))
        include_tags = parsed_args["includeTags"]
        max_tags = 500
        repo = model.get_repo(
            namespace, repository, get_authenticated_user(), include_tags, max_tags
        )
        if repo is None:
            raise NotFound()

        has_write_permission = ModifyRepositoryPermission(namespace, repository).can()
        has_write_permission = has_write_permission and repo.state == RepositoryState.NORMAL

        repo_data = repo.to_dict()
        repo_data["can_write"] = has_write_permission
        repo_data["can_admin"] = AdministerRepositoryPermission(namespace, repository).can()

        if parsed_args["includeStats"] and repo.repository_base_elements.kind_name != "application":
            stats = []
            found_dates = {}

            for count in repo.counts:
                stats.append(count.to_dict())
                found_dates["%s/%s" % (count.date.month, count.date.day)] = True

            # Fill in any missing stats with zeros.
            for day in range(1, MAX_DAYS_IN_3_MONTHS):
                day_date = datetime.now() - timedelta(days=day)
                key = "%s/%s" % (day_date.month, day_date.day)
                if key not in found_dates:
                    stats.append(
                        {"date": day_date.date().isoformat(), "count": 0,}
                    )

            repo_data["stats"] = stats
        return repo_data

    @require_repo_write
    @nickname("updateRepo")
    @validate_json_request("RepoUpdate")
    def put(self, namespace, repository):
        """
        Update the description in the specified repository.
        """
        if not model.repo_exists(namespace, repository):
            raise NotFound()

        values = request.get_json()
        model.set_description(namespace, repository, values["description"])

        log_action(
            "set_repo_description",
            namespace,
            {"repo": repository, "namespace": namespace, "description": values["description"]},
            repo_name=repository,
        )
        return {"success": True}

    @require_repo_admin
    @nickname("deleteRepository")
    def delete(self, namespace, repository):
        """
        Delete a repository.
        """
        username = model.mark_repository_for_deletion(namespace, repository, repository_gc_queue)

        if features.BILLING:
            plan = get_namespace_plan(namespace)
            model.check_repository_usage(username, plan)

        # Remove any builds from the queue.
        dockerfile_build_queue.delete_namespaced_items(namespace, repository)

        log_action("delete_repo", namespace, {"repo": repository, "namespace": namespace})
        return "", 204


@resource("/v1/repository/<apirepopath:repository>/changevisibility")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
class RepositoryVisibility(RepositoryParamResource):
    """
    Custom verb for changing the visibility of the repository.
    """

    schemas = {
        "ChangeVisibility": {
            "type": "object",
            "description": "Change the visibility for the repository.",
            "required": ["visibility",],
            "properties": {
                "visibility": {
                    "type": "string",
                    "description": "Visibility which the repository will start with",
                    "enum": ["public", "private",],
                },
            },
        }
    }

    @require_repo_admin
    @nickname("changeRepoVisibility")
    @validate_json_request("ChangeVisibility")
    def post(self, namespace, repository):
        """
        Change the visibility of a repository.
        """
        if model.repo_exists(namespace, repository):
            values = request.get_json()
            visibility = values["visibility"]
            if visibility == "private":
                check_allowed_private_repos(namespace)

            model.set_repository_visibility(namespace, repository, visibility)
            log_action(
                "change_repo_visibility",
                namespace,
                {"repo": repository, "namespace": namespace, "visibility": values["visibility"]},
                repo_name=repository,
            )
            return {"success": True}


@resource("/v1/repository/<apirepopath:repository>/changetrust")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
class RepositoryTrust(RepositoryParamResource):
    """
    Custom verb for changing the trust settings of the repository.
    """

    schemas = {
        "ChangeRepoTrust": {
            "type": "object",
            "description": "Change the trust settings for the repository.",
            "required": ["trust_enabled",],
            "properties": {
                "trust_enabled": {
                    "type": "boolean",
                    "description": "Whether or not signing is enabled for the repository.",
                },
            },
        }
    }

    @show_if(features.SIGNING)
    @require_repo_admin
    @nickname("changeRepoTrust")
    @validate_json_request("ChangeRepoTrust")
    def post(self, namespace, repository):
        """
        Change the visibility of a repository.
        """
        if not model.repo_exists(namespace, repository):
            raise NotFound()

        tags, _ = tuf_metadata_api.get_default_tags_with_expiration(namespace, repository)
        if tags and not tuf_metadata_api.delete_metadata(namespace, repository):
            raise DownstreamIssue("Unable to delete downstream trust metadata")

        values = request.get_json()
        model.set_trust(namespace, repository, values["trust_enabled"])

        log_action(
            "change_repo_trust",
            namespace,
            {"repo": repository, "namespace": namespace, "trust_enabled": values["trust_enabled"]},
            repo_name=repository,
        )

        return {"success": True}


@resource("/v1/repository/<apirepopath:repository>/changestate")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@show_if(features.REPO_MIRROR)
class RepositoryStateResource(RepositoryParamResource):
    """
    Custom verb for changing the state of the repository.
    """

    schemas = {
        "ChangeRepoState": {
            "type": "object",
            "description": "Change the state of the repository.",
            "required": ["state"],
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Determines whether pushes are allowed.",
                    "enum": ["NORMAL", "READ_ONLY", "MIRROR"],
                },
            },
        }
    }

    @require_repo_admin
    @nickname("changeRepoState")
    @validate_json_request("ChangeRepoState")
    def put(self, namespace, repository):
        """
        Change the state of a repository.
        """
        if not model.repo_exists(namespace, repository):
            raise NotFound()

        values = request.get_json()
        state_name = values["state"]

        try:
            state = RepositoryState[state_name]
        except KeyError:
            state = None

        if state == RepositoryState.MIRROR and not features.REPO_MIRROR:
            return {"detail": "Unknown Repository State: %s" % state_name}, 400

        if state is None:
            return {"detail": "%s is not a valid Repository state." % state_name}, 400

        model.set_repository_state(namespace, repository, state)

        log_action(
            "change_repo_state",
            namespace,
            {"repo": repository, "namespace": namespace, "state_changed": state_name},
            repo_name=repository,
        )

        return {"success": True}
