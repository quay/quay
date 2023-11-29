"""
Manage the tags of a repository.
"""
from datetime import datetime

from flask import abort, request

from app import app, docker_v2_signing_key, model_cache, storage
from auth.auth_context import get_authenticated_user
from data.model import repository as repository_model
from data.registry_model import registry_model
from endpoints.api import RepositoryParamResource
from endpoints.api import abort as custom_abort
from endpoints.api import (
    deprecated,
    disallow_for_app_repositories,
    disallow_for_non_normal_repositories,
    disallow_for_user_namespace,
    format_date,
    log_action,
    nickname,
    parse_args,
    path_param,
    query_param,
    require_repo_read,
    require_repo_write,
    resource,
    show_if,
    validate_json_request,
)
from endpoints.exception import InvalidRequest, NotFound
from util.names import TAG_ERROR, TAG_REGEX
from util.parsing import truthy_bool


def _tag_dict(tag):
    tag_info = {
        "name": tag.name,
        "reversion": tag.reversion,
    }

    if tag.lifetime_start_ts and tag.lifetime_start_ts > 0:
        tag_info["start_ts"] = tag.lifetime_start_ts

    if tag.lifetime_end_ts and tag.lifetime_end_ts > 0:
        tag_info["end_ts"] = tag.lifetime_end_ts

    tag_info["manifest_digest"] = tag.manifest_digest
    tag_info["is_manifest_list"] = tag.manifest.is_manifest_list
    tag_info["size"] = tag.manifest_layers_size

    if tag.lifetime_start_ts and tag.lifetime_start_ts > 0:
        last_modified = format_date(datetime.utcfromtimestamp(tag.lifetime_start_ts))
        tag_info["last_modified"] = last_modified

    if tag.lifetime_end_ts is not None:
        expiration = format_date(datetime.utcfromtimestamp(tag.lifetime_end_ts))
        tag_info["expiration"] = expiration

    return tag_info


@resource("/v1/repository/<apirepopath:repository>/tag/")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
class ListRepositoryTags(RepositoryParamResource):
    """
    Resource for listing full repository tag history, alive *and dead*.
    """

    @require_repo_read(allow_for_superuser=True)
    @disallow_for_app_repositories
    @parse_args()
    @query_param("specificTag", "Filters the tags to the specific tag.", type=str, default="")
    @query_param(
        "filter_tag_name",
        "Syntax: <op>:<name> Filters the tag names based on the operation."
        "<op> can be 'like' or 'eq'.",
        type=str,
        default="",
    )
    @query_param(
        "limit", "Limit to the number of results to return per page. Max 100.", type=int, default=50
    )
    @query_param("page", "Page index for the results. Default 1.", type=int, default=1)
    @query_param("onlyActiveTags", "Filter to only active tags.", type=truthy_bool, default=False)
    @nickname("listRepoTags")
    def get(self, namespace, repository, parsed_args):
        specific_tag = parsed_args.get("specificTag") or None
        filter_tag_name = parsed_args.get("filter_tag_name") or None
        page = max(1, parsed_args.get("page", 1))
        limit = min(100, max(1, parsed_args.get("limit", 50)))
        active_tags_only = parsed_args.get("onlyActiveTags")

        repo_ref = registry_model.lookup_repository(namespace, repository)
        if repo_ref is None:
            raise NotFound()
        try:
            history, has_more = registry_model.list_repository_tag_history(
                repo_ref,
                page=page,
                size=limit,
                specific_tag_name=specific_tag,
                active_tags_only=active_tags_only,
                filter_tag_name=filter_tag_name,
            )
        except ValueError as error:
            print("error", error)
            custom_abort(400, message=str(error))

        return {
            "tags": [_tag_dict(tag) for tag in history],
            "page": page,
            "has_additional": has_more,
        }


@resource("/v1/repository/<apirepopath:repository>/tag/<tag>")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("tag", "The name of the tag")
class RepositoryTag(RepositoryParamResource):
    """
    Resource for managing repository tags.
    """

    schemas = {
        "ChangeTag": {
            "type": "object",
            "description": "Makes changes to a specific tag",
            "properties": {
                "manifest_digest": {
                    "type": ["string", "null"],
                    "description": "(If specified) The manifest digest to which the tag should point",
                },
                "expiration": {
                    "type": ["number", "null"],
                    "description": "(If specified) The expiration for the image",
                },
            },
        },
    }

    @require_repo_write(allow_for_superuser=True)
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    @disallow_for_user_namespace
    @nickname("changeTag")
    @validate_json_request("ChangeTag")
    def put(self, namespace, repository, tag):
        """
        Change which image a tag points to or create a new tag.
        """
        if not TAG_REGEX.match(tag):
            abort(400, TAG_ERROR)

        repo_ref = registry_model.lookup_repository(namespace, repository)
        if repo_ref is None:
            raise NotFound()

        if "expiration" in request.get_json():
            tag_ref = registry_model.get_repo_tag(repo_ref, tag)
            if tag_ref is None:
                raise NotFound()

            expiration = request.get_json().get("expiration")
            expiration_date = None
            if expiration is not None:
                try:
                    expiration_date = datetime.utcfromtimestamp(float(expiration))
                except ValueError:
                    abort(400)

                if expiration_date <= datetime.now():
                    abort(400)

            existing_end_ts, ok = registry_model.change_repository_tag_expiration(
                tag_ref, expiration_date
            )
            if ok:
                if not (existing_end_ts is None and expiration_date is None):
                    log_action(
                        "change_tag_expiration",
                        namespace,
                        {
                            "username": get_authenticated_user().username,
                            "repo": repository,
                            "tag": tag,
                            "namespace": namespace,
                            "expiration_date": expiration_date,
                            "old_expiration_date": existing_end_ts,
                        },
                        repo_name=repository,
                    )
            else:
                raise InvalidRequest("Could not update tag expiration; Tag has probably changed")

        if "manifest_digest" in request.get_json():
            existing_tag = registry_model.get_repo_tag(repo_ref, tag)

            manifest_digest = None

            manifest_digest = request.get_json()["manifest_digest"]
            manifest = registry_model.lookup_manifest_by_digest(
                repo_ref, manifest_digest, require_available=True
            )

            if manifest is None:
                raise NotFound()

            existing_manifest = (
                registry_model.get_manifest_for_tag(existing_tag) if existing_tag else None
            )
            existing_manifest_digest = existing_manifest.digest if existing_manifest else None

            if not registry_model.retarget_tag(
                repo_ref, tag, manifest, storage, docker_v2_signing_key
            ):
                raise InvalidRequest("Could not move tag")

            username = get_authenticated_user().username

            log_action(
                "move_tag" if existing_tag else "create_tag",
                namespace,
                {
                    "username": username,
                    "repo": repository,
                    "tag": tag,
                    "namespace": namespace,
                    "manifest_digest": manifest_digest,
                    "original_manifest_digest": existing_manifest_digest,
                },
                repo_name=repository,
            )

        return "Updated", 201

    @require_repo_write(allow_for_superuser=True)
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    @disallow_for_user_namespace
    @nickname("deleteFullTag")
    def delete(self, namespace, repository, tag):
        """
        Delete the specified repository tag.
        """

        repo_ref = registry_model.lookup_repository(namespace, repository)
        if repo_ref is None:
            raise NotFound()

        tag_ref = registry_model.delete_tag(model_cache, repo_ref, tag)
        if tag_ref is None:
            raise NotFound()

        username = get_authenticated_user().username
        log_action(
            "delete_tag",
            namespace,
            {"username": username, "repo": repository, "namespace": namespace, "tag": tag},
            repo_name=repository,
        )

        return "", 204


@resource("/v1/repository/<apirepopath:repository>/tag/<tag>/restore")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("tag", "The name of the tag")
class RestoreTag(RepositoryParamResource):
    """
    Resource for restoring a repository tag back to a previous image.
    """

    schemas = {
        "RestoreTag": {
            "type": "object",
            "description": "Restores a tag to a specific image",
            "properties": {
                "manifest_digest": {
                    "type": "string",
                    "description": "If specified, the manifest digest that should be used",
                },
            },
        },
    }

    @require_repo_write(allow_for_superuser=True)
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    @disallow_for_user_namespace
    @nickname("restoreTag")
    @validate_json_request("RestoreTag")
    def post(self, namespace, repository, tag):
        """
        Restores a repository tag back to a previous image in the repository.
        """
        repo_ref = registry_model.lookup_repository(namespace, repository)
        if repo_ref is None:
            raise NotFound()

        # Restore the tag back to the previous image.
        manifest_digest = request.get_json().get("manifest_digest", None)

        if manifest_digest is None:
            raise InvalidRequest("Missing manifest_digest")

        # Data for logging the reversion/restoration.
        username = get_authenticated_user().username
        log_data = {
            "username": username,
            "repo": repository,
            "tag": tag,
            "manifest_digest": manifest_digest,
        }

        manifest = registry_model.lookup_manifest_by_digest(
            repo_ref, manifest_digest, allow_dead=True, require_available=True
        )

        if manifest is None:
            raise NotFound()

        if not registry_model.retarget_tag(
            repo_ref,
            tag,
            manifest,
            storage,
            docker_v2_signing_key,
            is_reversion=True,
        ):
            raise InvalidRequest("Could not restore tag")

        log_action("revert_tag", namespace, log_data, repo_name=repository)

        return {}


@resource("/v1/repository/<apirepopath:repository>/tag/<tag>/expire")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("tag", "The name of the tag")
@show_if(app.config.get("PERMANENTLY_DELETE_TAGS", True))
class TagTimeMachineDelete(RepositoryParamResource):
    """
    Resource for updating the expiry of tags outside the time machine window
    """

    schemas = {
        "ExpireTag": {
            "type": "object",
            "description": "Removes tag from the time machine window",
            "properties": {
                "manifest_digest": {
                    "type": "string",
                    "description": "Required if is_alive set to false. If specified, the manifest digest that should be used. Ignored when setting alive to true.",
                },
                "include_submanifests": {
                    "type": "boolean",
                    "description": "If set to true, expire the sub-manifests as well",
                },
                "is_alive": {
                    "type": "boolean",
                    "description": "If true, set the expiry of the matching alive tag outside the time machine window. If false set the expiry of any expired tags with the same tag and manifest outside the time machine window.",
                },
            },
        },
    }

    @require_repo_write(allow_for_superuser=True)
    @disallow_for_app_repositories
    @nickname("removeTagFromTimemachine")
    @validate_json_request("ExpireTag")
    def post(self, namespace, repository, tag):
        """
        Updates any expired tags with the matching name and manifest with an expiry outside the time machine window
        """
        repo_ref = registry_model.lookup_repository(namespace, repository)
        if repo_ref is None:
            raise NotFound()

        alive = request.get_json().get("is_alive", False)
        manifest_digest = request.get_json().get("manifest_digest", None)
        if not alive and manifest_digest is None:
            raise InvalidRequest("manifest_digest required when is_alive set to false")

        manifest_ref = None
        if alive:
            existing_tag = registry_model.get_repo_tag(repo_ref, tag)
            if existing_tag is None:
                raise NotFound()
            manifest_ref = existing_tag.manifest
        else:
            manifest_ref = registry_model.lookup_manifest_by_digest(
                repo_ref, manifest_digest, allow_dead=True
            )
            if manifest_ref is None:
                raise NotFound()

        include_submanifests = request.get_json().get("include_submanifests", False)
        tags_updated = registry_model.remove_tag_from_timemachine(
            repo_ref, tag, manifest_ref, include_submanifests, alive
        )
        if not tags_updated:
            raise NotFound()

        username = get_authenticated_user().username
        log_action(
            "permanently_delete_tag",
            namespace,
            {
                "username": username,
                "repo": repository,
                "namespace": namespace,
                "tag": tag,
                "manifest_digest": manifest_ref.digest,
            },
            repo_name=repository,
        )
        return "", 200
