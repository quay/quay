"""
Manage the tags of a repository.
"""
from datetime import datetime
from flask import request, abort

from app import storage, docker_v2_signing_key
from auth.auth_context import get_authenticated_user
from data.registry_model import registry_model
from endpoints.api import (
    resource,
    nickname,
    require_repo_read,
    require_repo_write,
    RepositoryParamResource,
    log_action,
    validate_json_request,
    path_param,
    parse_args,
    query_param,
    truthy_bool,
    disallow_for_app_repositories,
    format_date,
    disallow_for_non_normal_repositories,
)
from endpoints.api.image import image_dict
from endpoints.exception import NotFound, InvalidRequest
from util.names import TAG_ERROR, TAG_REGEX


def _tag_dict(tag):
    tag_info = {
        "name": tag.name,
        "reversion": tag.reversion,
    }

    if tag.lifetime_start_ts and tag.lifetime_start_ts > 0:
        tag_info["start_ts"] = tag.lifetime_start_ts

    if tag.lifetime_end_ts and tag.lifetime_end_ts > 0:
        tag_info["end_ts"] = tag.lifetime_end_ts

    # TODO: Remove this once fully on OCI data model.
    if tag.legacy_image_if_present:
        tag_info["docker_image_id"] = tag.legacy_image.docker_image_id
        tag_info["image_id"] = tag.legacy_image.docker_image_id
        tag_info["size"] = tag.legacy_image.aggregate_size

    # TODO: Remove this check once fully on OCI data model.
    if tag.manifest_digest:
        tag_info["manifest_digest"] = tag.manifest_digest

        if tag.manifest:
            tag_info["is_manifest_list"] = tag.manifest.is_manifest_list

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

    @require_repo_read
    @disallow_for_app_repositories
    @parse_args()
    @query_param("specificTag", "Filters the tags to the specific tag.", type=str, default="")
    @query_param(
        "limit", "Limit to the number of results to return per page. Max 100.", type=int, default=50
    )
    @query_param("page", "Page index for the results. Default 1.", type=int, default=1)
    @query_param("onlyActiveTags", "Filter to only active tags.", type=truthy_bool, default=False)
    @nickname("listRepoTags")
    def get(self, namespace, repository, parsed_args):
        specific_tag = parsed_args.get("specificTag") or None
        page = max(1, parsed_args.get("page", 1))
        limit = min(100, max(1, parsed_args.get("limit", 50)))
        active_tags_only = parsed_args.get("onlyActiveTags")

        repo_ref = registry_model.lookup_repository(namespace, repository)
        if repo_ref is None:
            raise NotFound()

        history, has_more = registry_model.list_repository_tag_history(
            repo_ref,
            page=page,
            size=limit,
            specific_tag_name=specific_tag,
            active_tags_only=active_tags_only,
        )
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
                "image": {
                    "type": ["string", "null"],
                    "description": "(Deprecated: Use `manifest_digest`) Image to which the tag should point.",
                },
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

    @require_repo_write
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
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

        if "image" in request.get_json() or "manifest_digest" in request.get_json():
            existing_tag = registry_model.get_repo_tag(repo_ref, tag, include_legacy_image=True)

            manifest_or_image = None
            image_id = None
            manifest_digest = None

            if "image" in request.get_json():
                image_id = request.get_json()["image"]
                manifest_or_image = registry_model.get_legacy_image(repo_ref, image_id)
            else:
                manifest_digest = request.get_json()["manifest_digest"]
                manifest_or_image = registry_model.lookup_manifest_by_digest(
                    repo_ref, manifest_digest, require_available=True
                )

            if manifest_or_image is None:
                raise NotFound()

            # TODO: Remove this check once fully on V22
            existing_manifest_digest = None
            if existing_tag:
                existing_manifest = registry_model.get_manifest_for_tag(existing_tag)
                existing_manifest_digest = existing_manifest.digest if existing_manifest else None

            if not registry_model.retarget_tag(
                repo_ref, tag, manifest_or_image, storage, docker_v2_signing_key
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
                    "image": image_id,
                    "manifest_digest": manifest_digest,
                    "original_image": (
                        existing_tag.legacy_image.docker_image_id
                        if existing_tag and existing_tag.legacy_image_if_present
                        else None
                    ),
                    "original_manifest_digest": existing_manifest_digest,
                },
                repo_name=repository,
            )

        return "Updated", 201

    @require_repo_write
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    @nickname("deleteFullTag")
    def delete(self, namespace, repository, tag):
        """
        Delete the specified repository tag.
        """
        repo_ref = registry_model.lookup_repository(namespace, repository)
        if repo_ref is None:
            raise NotFound()

        registry_model.delete_tag(repo_ref, tag)

        username = get_authenticated_user().username
        log_action(
            "delete_tag",
            namespace,
            {"username": username, "repo": repository, "namespace": namespace, "tag": tag},
            repo_name=repository,
        )

        return "", 204


@resource("/v1/repository/<apirepopath:repository>/tag/<tag>/images")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("tag", "The name of the tag")
class RepositoryTagImages(RepositoryParamResource):
    """
    Resource for listing the images in a specific repository tag.
    """

    @require_repo_read
    @nickname("listTagImages")
    @disallow_for_app_repositories
    @parse_args()
    @query_param(
        "owned",
        "If specified, only images wholely owned by this tag are returned.",
        type=truthy_bool,
        default=False,
    )
    def get(self, namespace, repository, tag, parsed_args):
        """
        List the images for the specified repository tag.
        """
        repo_ref = registry_model.lookup_repository(namespace, repository)
        if repo_ref is None:
            raise NotFound()

        tag_ref = registry_model.get_repo_tag(repo_ref, tag, include_legacy_image=True)
        if tag_ref is None:
            raise NotFound()

        if tag_ref.legacy_image_if_present is None:
            return {"images": []}

        image_id = tag_ref.legacy_image.docker_image_id

        all_images = None
        if parsed_args["owned"]:
            # TODO: Remove the `owned` image concept once we are fully on V2_2.
            all_images = registry_model.get_legacy_images_owned_by_tag(tag_ref)
        else:
            image_with_parents = registry_model.get_legacy_image(
                repo_ref, image_id, include_parents=True
            )
            if image_with_parents is None:
                raise NotFound()

            all_images = [image_with_parents] + image_with_parents.parents

        return {
            "images": [image_dict(image) for image in all_images],
        }


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
                "image": {
                    "type": "string",
                    "description": "(Deprecated: use `manifest_digest`) Image to which the tag should point",
                },
                "manifest_digest": {
                    "type": "string",
                    "description": "If specified, the manifest digest that should be used",
                },
            },
        },
    }

    @require_repo_write
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
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
        image_id = request.get_json().get("image", None)
        manifest_digest = request.get_json().get("manifest_digest", None)

        if image_id is None and manifest_digest is None:
            raise InvalidRequest("Missing manifest_digest")

        # Data for logging the reversion/restoration.
        username = get_authenticated_user().username
        log_data = {
            "username": username,
            "repo": repository,
            "tag": tag,
            "image": image_id,
            "manifest_digest": manifest_digest,
        }

        manifest_or_legacy_image = None
        if manifest_digest is not None:
            manifest_or_legacy_image = registry_model.lookup_manifest_by_digest(
                repo_ref, manifest_digest, allow_dead=True, require_available=True
            )
        elif image_id is not None:
            manifest_or_legacy_image = registry_model.get_legacy_image(repo_ref, image_id)

        if manifest_or_legacy_image is None:
            raise NotFound()

        if not registry_model.retarget_tag(
            repo_ref,
            tag,
            manifest_or_legacy_image,
            storage,
            docker_v2_signing_key,
            is_reversion=True,
        ):
            raise InvalidRequest("Could not restore tag")

        log_action("revert_tag", namespace, log_data, repo_name=repository)

        return {}
