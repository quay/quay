import logging
import json

from flask import abort, request, jsonify, make_response, session

from app import storage, docker_v2_signing_key
from auth.decorators import process_auth
from auth.permissions import ReadRepositoryPermission, ModifyRepositoryPermission
from data.registry_model import registry_model
from data.registry_model.manifestbuilder import lookup_manifest_builder
from endpoints.decorators import (
    anon_protect,
    parse_repository_name,
    check_repository_state,
    check_readonly,
)
from endpoints.v1 import v1_bp, check_v1_push_enabled
from util.audit import track_and_log
from util.names import TAG_ERROR, TAG_REGEX

logger = logging.getLogger(__name__)


@v1_bp.route("/repositories/<repopath:repository>/tags", methods=["GET"])
@process_auth
@anon_protect
@parse_repository_name()
def get_tags(namespace_name, repo_name):
    permission = ReadRepositoryPermission(namespace_name, repo_name)
    repository_ref = registry_model.lookup_repository(
        namespace_name, repo_name, kind_filter="image"
    )
    if permission.can() or (repository_ref is not None and repository_ref.is_public):
        if repository_ref is None:
            abort(404)

        tag_map = registry_model.get_legacy_tags_map(repository_ref, storage)
        return jsonify(tag_map)

    abort(403)


@v1_bp.route("/repositories/<repopath:repository>/tags/<tag>", methods=["GET"])
@process_auth
@anon_protect
@parse_repository_name()
def get_tag(namespace_name, repo_name, tag):
    permission = ReadRepositoryPermission(namespace_name, repo_name)
    repository_ref = registry_model.lookup_repository(
        namespace_name, repo_name, kind_filter="image"
    )
    if permission.can() or (repository_ref is not None and repository_ref.is_public):
        if repository_ref is None:
            abort(404)

        image_id = registry_model.get_tag_legacy_image_id(repository_ref, tag, storage)
        if image_id is None:
            abort(404)

        resp = make_response('"%s"' % image_id)
        resp.headers["Content-Type"] = "application/json"
        return resp

    abort(403)


@v1_bp.route("/repositories/<repopath:repository>/tags/<tag>", methods=["PUT"])
@process_auth
@anon_protect
@parse_repository_name()
@check_repository_state
@check_v1_push_enabled()
@check_readonly
def put_tag(namespace_name, repo_name, tag):
    permission = ModifyRepositoryPermission(namespace_name, repo_name)
    repository_ref = registry_model.lookup_repository(
        namespace_name, repo_name, kind_filter="image"
    )

    if permission.can() and repository_ref is not None:
        if not TAG_REGEX.match(tag):
            abort(400, TAG_ERROR)

        image_id = json.loads(request.data)

        # Check for the image ID first in a builder (for an in-progress push).
        builder = lookup_manifest_builder(
            repository_ref, session.get("manifest_builder"), storage, docker_v2_signing_key
        )
        if builder is not None:
            layer = builder.lookup_layer(image_id)
            if layer is not None:
                commited_tag = builder.commit_tag_and_manifest(tag, layer)
                if commited_tag is None:
                    abort(400)

                return make_response("Created", 200)

        # Check if there is an existing image we should use (for PUT calls outside of a normal push
        # operation).
        legacy_image = registry_model.get_legacy_image(repository_ref, image_id, storage)
        if legacy_image is None:
            abort(400)

        if (
            registry_model.retarget_tag(
                repository_ref, tag, legacy_image, storage, docker_v2_signing_key
            )
            is None
        ):
            abort(400)

        return make_response("Created", 200)

    abort(403)


@v1_bp.route("/repositories/<repopath:repository>/tags/<tag>", methods=["DELETE"])
@process_auth
@anon_protect
@parse_repository_name()
@check_repository_state
@check_v1_push_enabled()
@check_readonly
def delete_tag(namespace_name, repo_name, tag):
    permission = ModifyRepositoryPermission(namespace_name, repo_name)
    repository_ref = registry_model.lookup_repository(
        namespace_name, repo_name, kind_filter="image"
    )

    if permission.can() and repository_ref is not None:
        if not registry_model.delete_tag(repository_ref, tag):
            abort(404)

        track_and_log("delete_tag", repository_ref, tag=tag)
        return make_response("Deleted", 200)

    abort(403)
