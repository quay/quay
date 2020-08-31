"""
Manage the manifests of a repository.
"""
import json
import logging

from datetime import datetime
from flask import request

from app import label_validator, storage
from data.model import InvalidLabelKeyException, InvalidMediaTypeException
from data.registry_model import registry_model
from digest import digest_tools
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
    abort,
    api,
    disallow_for_app_repositories,
    format_date,
    disallow_for_non_normal_repositories,
)
from endpoints.api.image import image_dict
from endpoints.exception import NotFound
from util.validation import VALID_LABEL_KEY_REGEX


BASE_MANIFEST_ROUTE = '/v1/repository/<apirepopath:repository>/manifest/<regex("{0}"):manifestref>'
MANIFEST_DIGEST_ROUTE = BASE_MANIFEST_ROUTE.format(digest_tools.DIGEST_PATTERN)
ALLOWED_LABEL_MEDIA_TYPES = ["text/plain", "application/json"]


logger = logging.getLogger(__name__)


def _label_dict(label):
    return {
        "id": label.uuid,
        "key": label.key,
        "value": label.value,
        "source_type": label.source_type_name,
        "media_type": label.media_type_name,
    }


def _layer_dict(manifest_layer, index):
    # NOTE: The `command` in the layer is either a JSON string of an array (schema 1) or
    # a single string (schema 2). The block below normalizes it to have the same format.
    command = None
    if manifest_layer.command:
        try:
            command = json.loads(manifest_layer.command)
        except (TypeError, ValueError):
            command = [manifest_layer.command]

    return {
        "index": index,
        "compressed_size": manifest_layer.compressed_size,
        "is_remote": manifest_layer.is_remote,
        "urls": manifest_layer.urls,
        "command": command,
        "comment": manifest_layer.comment,
        "author": manifest_layer.author,
        "blob_digest": str(manifest_layer.blob_digest),
        "created_datetime": format_date(manifest_layer.created_datetime),
    }


def _manifest_dict(manifest):
    layers = None
    if not manifest.is_manifest_list:
        layers = registry_model.list_manifest_layers(manifest, storage)
        if layers is None:
            logger.debug("Missing layers for manifest `%s`", manifest.digest)
            abort(404)

    image = None
    if manifest.legacy_image_root_id:
        # NOTE: This is replicating our older response for this endpoint, but
        # returns empty for the metadata fields. This is to ensure back-compat
        # for callers still using the deprecated API.
        image = {
            "id": manifest.legacy_image_root_id,
            "created": format_date(datetime.utcnow()),
            "comment": "",
            "command": "",
            "size": 0,
            "uploading": False,
            "sort_index": 0,
            "ancestors": "",
        }

    return {
        "digest": manifest.digest,
        "is_manifest_list": manifest.is_manifest_list,
        "manifest_data": manifest.internal_manifest_bytes.as_unicode(),
        "layers": (
            [_layer_dict(lyr.layer_info, idx) for idx, lyr in enumerate(layers)] if layers else None
        ),
        "image": image,
    }


@resource(MANIFEST_DIGEST_ROUTE)
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("manifestref", "The digest of the manifest")
class RepositoryManifest(RepositoryParamResource):
    """
    Resource for retrieving a specific repository manifest.
    """

    @require_repo_read
    @nickname("getRepoManifest")
    @disallow_for_app_repositories
    def get(self, namespace_name, repository_name, manifestref):
        repo_ref = registry_model.lookup_repository(namespace_name, repository_name)
        if repo_ref is None:
            raise NotFound()

        manifest = registry_model.lookup_manifest_by_digest(repo_ref, manifestref)
        if manifest is None:
            raise NotFound()

        return _manifest_dict(manifest)


@resource(MANIFEST_DIGEST_ROUTE + "/labels")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("manifestref", "The digest of the manifest")
class RepositoryManifestLabels(RepositoryParamResource):
    """
    Resource for listing the labels on a specific repository manifest.
    """

    schemas = {
        "AddLabel": {
            "type": "object",
            "description": "Adds a label to a manifest",
            "required": [
                "key",
                "value",
                "media_type",
            ],
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The key for the label",
                },
                "value": {
                    "type": "string",
                    "description": "The value for the label",
                },
                "media_type": {
                    "type": ["string", "null"],
                    "description": "The media type for this label",
                    "enum": ALLOWED_LABEL_MEDIA_TYPES + [None],
                },
            },
        },
    }

    @require_repo_read
    @nickname("listManifestLabels")
    @disallow_for_app_repositories
    @parse_args()
    @query_param(
        "filter",
        "If specified, only labels matching the given prefix will be returned",
        type=str,
        default=None,
    )
    def get(self, namespace_name, repository_name, manifestref, parsed_args):
        repo_ref = registry_model.lookup_repository(namespace_name, repository_name)
        if repo_ref is None:
            raise NotFound()

        manifest = registry_model.lookup_manifest_by_digest(repo_ref, manifestref)
        if manifest is None:
            raise NotFound()

        labels = registry_model.list_manifest_labels(manifest, parsed_args["filter"])
        if labels is None:
            raise NotFound()

        return {"labels": [_label_dict(label) for label in labels]}

    @require_repo_write
    @nickname("addManifestLabel")
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    @validate_json_request("AddLabel")
    def post(self, namespace_name, repository_name, manifestref):
        """
        Adds a new label into the tag manifest.
        """
        label_data = request.get_json()

        # Check for any reserved prefixes.
        if label_validator.has_reserved_prefix(label_data["key"]):
            abort(400, message="Label has a reserved prefix")

        repo_ref = registry_model.lookup_repository(namespace_name, repository_name)
        if repo_ref is None:
            raise NotFound()

        manifest = registry_model.lookup_manifest_by_digest(repo_ref, manifestref)
        if manifest is None:
            raise NotFound()

        label = None
        try:
            label = registry_model.create_manifest_label(
                manifest, label_data["key"], label_data["value"], "api", label_data["media_type"]
            )
        except InvalidLabelKeyException:
            message = (
                "Label is of an invalid format or missing please "
                + "use %s format for labels" % VALID_LABEL_KEY_REGEX
            )
            abort(400, message=message)
        except InvalidMediaTypeException:
            message = (
                "Media type is invalid please use a valid media type: text/plain, application/json"
            )
            abort(400, message=message)

        if label is None:
            raise NotFound()

        metadata = {
            "id": label.uuid,
            "key": label.key,
            "value": label.value,
            "manifest_digest": manifestref,
            "media_type": label.media_type_name,
            "namespace": namespace_name,
            "repo": repository_name,
        }

        log_action("manifest_label_add", namespace_name, metadata, repo_name=repository_name)

        resp = {"label": _label_dict(label)}
        repo_string = "%s/%s" % (namespace_name, repository_name)
        headers = {
            "Location": api.url_for(
                ManageRepositoryManifestLabel,
                repository=repo_string,
                manifestref=manifestref,
                labelid=label.uuid,
            ),
        }
        return resp, 201, headers


@resource(MANIFEST_DIGEST_ROUTE + "/labels/<labelid>")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("manifestref", "The digest of the manifest")
@path_param("labelid", "The ID of the label")
class ManageRepositoryManifestLabel(RepositoryParamResource):
    """
    Resource for managing the labels on a specific repository manifest.
    """

    @require_repo_read
    @nickname("getManifestLabel")
    @disallow_for_app_repositories
    def get(self, namespace_name, repository_name, manifestref, labelid):
        """
        Retrieves the label with the specific ID under the manifest.
        """
        repo_ref = registry_model.lookup_repository(namespace_name, repository_name)
        if repo_ref is None:
            raise NotFound()

        manifest = registry_model.lookup_manifest_by_digest(repo_ref, manifestref)
        if manifest is None:
            raise NotFound()

        label = registry_model.get_manifest_label(manifest, labelid)
        if label is None:
            raise NotFound()

        return _label_dict(label)

    @require_repo_write
    @nickname("deleteManifestLabel")
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    def delete(self, namespace_name, repository_name, manifestref, labelid):
        """
        Deletes an existing label from a manifest.
        """
        repo_ref = registry_model.lookup_repository(namespace_name, repository_name)
        if repo_ref is None:
            raise NotFound()

        manifest = registry_model.lookup_manifest_by_digest(repo_ref, manifestref)
        if manifest is None:
            raise NotFound()

        deleted = registry_model.delete_manifest_label(manifest, labelid)
        if deleted is None:
            raise NotFound()

        metadata = {
            "id": labelid,
            "key": deleted.key,
            "value": deleted.value,
            "manifest_digest": manifestref,
            "namespace": namespace_name,
            "repo": repository_name,
        }

        log_action("manifest_label_delete", namespace_name, metadata, repo_name=repository_name)
        return "", 204
