"""
Manage the manifests of a repository.
"""
import io
import json
import logging
import tarfile
from datetime import datetime
from typing import List, Optional

from flask import request

import features
from app import app, label_validator, storage
from data.model import InvalidLabelKeyException, InvalidMediaTypeException
from data.model.oci.retriever import RepositoryContentRetriever
from data.registry_model import registry_model
from digest import digest_tools
from endpoints.api import (
    RepositoryParamResource,
    abort,
    api,
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
    validate_json_request,
)
from endpoints.exception import NotFound
from util.parsing import truthy_bool
from util.validation import VALID_LABEL_KEY_REGEX

BASE_MANIFEST_ROUTE = '/v1/repository/<apirepopath:repository>/manifest/<regex("{0}"):manifestref>'
MANIFEST_DIGEST_ROUTE = BASE_MANIFEST_ROUTE.format(digest_tools.DIGEST_PATTERN)
ALLOWED_LABEL_MEDIA_TYPES: List[Optional[str]] = ["text/plain", "application/json"]


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

    return {
        "digest": manifest.digest,
        "is_manifest_list": manifest.is_manifest_list,
        "manifest_data": manifest.internal_manifest_bytes.as_unicode(),
        "config_media_type": manifest.config_media_type,
        "layers_compressed_size": manifest.layers_compressed_size
        if not manifest.is_manifest_list
        else 0,
        "layers": (
            [_layer_dict(lyr.layer_info, idx) for idx, lyr in enumerate(layers)] if layers else None
        ),
    }


@resource(MANIFEST_DIGEST_ROUTE)
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("manifestref", "The digest of the manifest")
class RepositoryManifest(RepositoryParamResource):
    """
    Resource for retrieving a specific repository manifest.
    """

    @require_repo_read(allow_for_superuser=True)
    @nickname("getRepoManifest")
    @disallow_for_app_repositories
    @parse_args()
    @query_param(
        "include_modelcard",
        "If specified, include modelcard markdown from image, if any",
        type=truthy_bool,
        default=False,
    )
    def get(self, namespace_name, repository_name, manifestref, parsed_args):
        repo_ref = registry_model.lookup_repository(namespace_name, repository_name)
        if repo_ref is None:
            raise NotFound()

        manifest = registry_model.lookup_manifest_by_digest(repo_ref, manifestref)
        # sub-manifests created via pull-thru proxy cache as part of a manifest list
        # pull will not contain the manifest bytes unless individually pulled.
        # to avoid a parsing error from `_manifest_dict`, we return a 404 either
        # when the manifest doesn't exist or if the manifest bytes are empty.
        if manifest is None or manifest.internal_manifest_bytes.as_unicode() == "":
            raise NotFound()

        manifest_dict = _manifest_dict(manifest)

        if features.UI_MODELCARD and parsed_args["include_modelcard"]:
            manifest_modelcard_annotation = app.config["UI_MODELCARD_ANNOTATION"]
            manifest_layer_modelcard_annotation = app.config["UI_MODELCARD_LAYER_ANNOTATION"]

            parsed = manifest.get_parsed_manifest()

            layer_digest = None
            if (
                parsed.artifact_type
                and manifest.artifact_type == app.config["UI_MODELCARD_ARTIFACT_TYPE"]
            ):
                layer_digest = str(parsed.filesystem_layers[-1].digest)

            elif (
                manifest_modelcard_annotation
                and hasattr(parsed, "annotations")
                and manifest_modelcard_annotation.items() <= parsed.annotations.items()
            ):
                for layer in parsed.filesystem_layers:
                    if (
                        hasattr(layer, "annotations")
                        and manifest_layer_modelcard_annotation.items() <= layer.annotations.items()
                    ):
                        layer_digest = layer.digest
                        break

            if layer_digest:
                retriever = RepositoryContentRetriever(repo_ref._db_id, storage)
                content = retriever.get_blob_bytes_with_digest(layer_digest)
                manifest_dict["modelcard"] = content.decode("utf-8")

        return manifest_dict


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

    @require_repo_read(allow_for_superuser=True)
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

    @require_repo_write(allow_for_superuser=True)
    @nickname("addManifestLabel")
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    @disallow_for_user_namespace
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

    @require_repo_read(allow_for_superuser=True)
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

    @require_repo_write(allow_for_superuser=True)
    @nickname("deleteManifestLabel")
    @disallow_for_app_repositories
    @disallow_for_non_normal_repositories
    @disallow_for_user_namespace
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
