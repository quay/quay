import logging
import json

from functools import wraps
from datetime import datetime
from time import time

from flask import make_response, request, session, Response, redirect, abort as flask_abort

from app import storage as store, app, docker_v2_signing_key
from auth.auth_context import get_authenticated_user
from auth.decorators import extract_namespace_repo_from_session, process_auth
from auth.permissions import ReadRepositoryPermission, ModifyRepositoryPermission
from data import database
from data.registry_model import registry_model
from data.registry_model.blobuploader import upload_blob, BlobUploadSettings, BlobUploadException
from data.registry_model.manifestbuilder import lookup_manifest_builder
from digest import checksums
from endpoints.metrics import image_pulled_bytes
from endpoints.v1 import v1_bp, check_v1_push_enabled
from endpoints.v1.index import ensure_namespace_enabled
from endpoints.decorators import (
    anon_protect,
    check_region_blacklisted,
    check_repository_state,
    check_readonly,
)
from util.http import abort
from util.registry.replication import queue_storage_replication
from util.request import get_request_ip


logger = logging.getLogger(__name__)


def require_completion(f):
    """
    This make sure that the image push correctly finished.
    """

    @wraps(f)
    def wrapper(namespace, repository, *args, **kwargs):
        # TODO: Remove this
        return f(namespace, repository, *args, **kwargs)

    return wrapper


def set_cache_headers(f):
    """
    Returns HTTP headers suitable for caching.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        # Set TTL to 1 year by default
        ttl = 31536000
        expires = datetime.fromtimestamp(int(time()) + ttl)
        expires = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
        headers = {
            "Cache-Control": "public, max-age={0}".format(ttl),
            "Expires": expires,
            "Last-Modified": "Thu, 01 Jan 1970 00:00:00 GMT",
        }
        if "If-Modified-Since" in request.headers:
            response = make_response("Not modified", 304)
            response.headers.extend(headers)
            return response
        kwargs["headers"] = headers
        # Prevent the Cookie to be sent when the object is cacheable
        session.modified = False
        return f(*args, **kwargs)

    return wrapper


@v1_bp.route("/images/<image_id>/layer", methods=["HEAD"])
@process_auth
@extract_namespace_repo_from_session
@ensure_namespace_enabled
@require_completion
@set_cache_headers
@anon_protect
def head_image_layer(namespace, repository, image_id, headers):
    permission = ReadRepositoryPermission(namespace, repository)
    repository_ref = registry_model.lookup_repository(namespace, repository, kind_filter="image")

    logger.debug("Checking repo permissions")
    if permission.can() or (repository_ref is not None and repository_ref.is_public):
        if repository_ref is None:
            abort(404)

        logger.debug("Looking up placement locations")
        legacy_image = registry_model.get_legacy_image(
            repository_ref, image_id, store, include_blob=True
        )
        if legacy_image is None:
            logger.debug("Could not find any blob placement locations")
            abort(404, "Image %(image_id)s not found", issue="unknown-image", image_id=image_id)

        # Add the Accept-Ranges header if the storage engine supports resumable
        # downloads.
        extra_headers = {}
        if store.get_supports_resumable_downloads(legacy_image.blob.placements):
            logger.debug("Storage supports resumable downloads")
            extra_headers["Accept-Ranges"] = "bytes"

        resp = make_response("")
        resp.headers.extend(headers)
        resp.headers.extend(extra_headers)
        return resp

    abort(403)


@v1_bp.route("/images/<image_id>/layer", methods=["GET"])
@process_auth
@extract_namespace_repo_from_session
@ensure_namespace_enabled
@require_completion
@set_cache_headers
@check_region_blacklisted()
@anon_protect
def get_image_layer(namespace, repository, image_id, headers):
    permission = ReadRepositoryPermission(namespace, repository)
    repository_ref = registry_model.lookup_repository(namespace, repository, kind_filter="image")

    logger.debug("Checking repo permissions")
    if permission.can() or (repository_ref is not None and repository_ref.is_public):
        if repository_ref is None:
            abort(404)

        legacy_image = registry_model.get_legacy_image(
            repository_ref, image_id, store, include_blob=True
        )
        if legacy_image is None:
            abort(404, "Image %(image_id)s not found", issue="unknown-image", image_id=image_id)

        path = legacy_image.blob.storage_path
        image_pulled_bytes.labels("v1").inc(legacy_image.blob.compressed_size)

        try:
            logger.debug("Looking up the direct download URL for path: %s", path)
            direct_download_url = store.get_direct_download_url(
                legacy_image.blob.placements, path, get_request_ip()
            )
            if direct_download_url:
                logger.debug("Returning direct download URL")
                resp = redirect(direct_download_url)
                return resp

            # Close the database handle here for this process before we send the long download.
            database.close_db_filter(None)
            logger.debug("Streaming layer data")
            return Response(store.stream_read(legacy_image.blob.placements, path), headers=headers)
        except (IOError, AttributeError):
            logger.exception("Image layer data not found")
            abort(404, "Image %(image_id)s not found", issue="unknown-image", image_id=image_id)

    abort(403)


@v1_bp.route("/images/<image_id>/layer", methods=["PUT"])
@process_auth
@extract_namespace_repo_from_session
@check_v1_push_enabled()
@ensure_namespace_enabled
@check_repository_state
@anon_protect
@check_readonly
def put_image_layer(namespace, repository, image_id):
    logger.debug("Checking repo permissions")
    permission = ModifyRepositoryPermission(namespace, repository)
    if not permission.can():
        abort(403)

    repository_ref = registry_model.lookup_repository(namespace, repository, kind_filter="image")
    if repository_ref is None:
        abort(403)

    logger.debug("Checking for image in manifest builder")
    builder = lookup_manifest_builder(
        repository_ref, session.get("manifest_builder"), store, docker_v2_signing_key
    )
    if builder is None:
        abort(400)

    layer = builder.lookup_layer(image_id)
    if layer is None:
        abort(404)

    logger.debug("Storing layer data")
    input_stream = request.stream
    if request.headers.get("transfer-encoding") == "chunked":
        # Careful, might work only with WSGI servers supporting chunked
        # encoding (Gunicorn)
        input_stream = request.environ["wsgi.input"]

    expiration_sec = app.config["PUSH_TEMP_TAG_EXPIRATION_SEC"]
    settings = BlobUploadSettings(
        maximum_blob_size=app.config["MAXIMUM_LAYER_SIZE"],
        committed_blob_expiration=expiration_sec,
    )

    extra_handlers = []

    # Add a handler that copies the data into a temp file. This is used to calculate the tarsum,
    # which is only needed for older versions of Docker.
    requires_tarsum = bool(builder.get_layer_checksums(layer))
    if requires_tarsum:
        tmp, tmp_hndlr = store.temp_store_handler()
        extra_handlers.append(tmp_hndlr)

    # Add a handler which computes the simple Docker V1 checksum.
    h, sum_hndlr = checksums.simple_checksum_handler(layer.v1_metadata_string)
    extra_handlers.append(sum_hndlr)

    uploaded_blob = None
    try:
        with upload_blob(
            repository_ref, store, settings, extra_blob_stream_handlers=extra_handlers
        ) as manager:
            manager.upload_chunk(app.config, input_stream)
            uploaded_blob = manager.commit_to_blob(app.config)
    except BlobUploadException:
        logger.exception("Exception when writing image data")
        abort(520, "Image %(image_id)s could not be written. Please try again.", image_id=image_id)

    # Compute the final checksum
    csums = []
    csums.append("sha256:{0}".format(h.hexdigest()))

    try:
        if requires_tarsum:
            tmp.seek(0)
            csums.append(checksums.compute_tarsum(tmp, layer.v1_metadata_string))
            tmp.close()
    except (IOError, checksums.TarError) as exc:
        logger.debug("put_image_layer: Error when computing tarsum %s", exc)

    # If there was already a precomputed checksum, validate against it now.
    if builder.get_layer_checksums(layer):
        checksum = builder.get_layer_checksums(layer)[0]
        if not builder.validate_layer_checksum(layer, checksum):
            logger.debug(
                "put_image_checksum: Wrong checksum. Given: %s and expected: %s",
                checksum,
                builder.get_layer_checksums(layer),
            )
            abort(
                400,
                "Checksum mismatch for image: %(image_id)s",
                issue="checksum-mismatch",
                image_id=image_id,
            )

    # Assign the blob to the layer in the manifest.
    if not builder.assign_layer_blob(layer, uploaded_blob, csums):
        abort(500, "Something went wrong")

    # Send a job to the work queue to replicate the image layer.
    # TODO: move this into a better place.
    queue_storage_replication(namespace, uploaded_blob)

    return make_response("true", 200)


@v1_bp.route("/images/<image_id>/checksum", methods=["PUT"])
@process_auth
@extract_namespace_repo_from_session
@check_v1_push_enabled()
@ensure_namespace_enabled
@check_repository_state
@anon_protect
@check_readonly
def put_image_checksum(namespace, repository, image_id):
    logger.debug("Checking repo permissions")
    permission = ModifyRepositoryPermission(namespace, repository)
    if not permission.can():
        abort(403)

    repository_ref = registry_model.lookup_repository(namespace, repository, kind_filter="image")
    if repository_ref is None:
        abort(403)

    # Docker Version < 0.10 (tarsum+sha):
    old_checksum = request.headers.get("X-Docker-Checksum")

    # Docker Version >= 0.10 (sha):
    new_checksum = request.headers.get("X-Docker-Checksum-Payload")

    checksum = new_checksum or old_checksum
    if not checksum:
        abort(
            400,
            "Missing checksum for image %(image_id)s",
            issue="missing-checksum",
            image_id=image_id,
        )

    logger.debug("Checking for image in manifest builder")
    builder = lookup_manifest_builder(
        repository_ref, session.get("manifest_builder"), store, docker_v2_signing_key
    )
    if builder is None:
        abort(400)

    layer = builder.lookup_layer(image_id)
    if layer is None:
        abort(404)

    if old_checksum:
        builder.save_precomputed_checksum(layer, checksum)
        return make_response("true", 200)

    if not builder.validate_layer_checksum(layer, checksum):
        logger.debug(
            "put_image_checksum: Wrong checksum. Given: %s and expected: %s",
            checksum,
            builder.get_layer_checksums(layer),
        )
        abort(
            400,
            "Checksum mismatch for image: %(image_id)s",
            issue="checksum-mismatch",
            image_id=image_id,
        )

    return make_response("true", 200)


@v1_bp.route("/images/<image_id>/json", methods=["GET"])
@process_auth
@extract_namespace_repo_from_session
@ensure_namespace_enabled
@require_completion
@set_cache_headers
@anon_protect
def get_image_json(namespace, repository, image_id, headers):
    logger.debug("Checking repo permissions")
    permission = ReadRepositoryPermission(namespace, repository)
    repository_ref = registry_model.lookup_repository(namespace, repository, kind_filter="image")
    if not permission.can() and not (repository_ref is not None and repository_ref.is_public):
        abort(403)

    logger.debug("Looking up repo image")
    legacy_image = registry_model.get_legacy_image(
        repository_ref, image_id, store, include_blob=True
    )
    if legacy_image is None:
        flask_abort(404)

    size = legacy_image.blob.compressed_size
    if size is not None:
        # Note: X-Docker-Size is optional and we *can* end up with a NULL image_size,
        # so handle this case rather than failing.
        headers["X-Docker-Size"] = str(size)

    response = make_response(legacy_image.v1_metadata_string, 200)
    response.headers.extend(headers)
    return response


@v1_bp.route("/images/<image_id>/ancestry", methods=["GET"])
@process_auth
@extract_namespace_repo_from_session
@ensure_namespace_enabled
@require_completion
@set_cache_headers
@anon_protect
def get_image_ancestry(namespace, repository, image_id, headers):
    logger.debug("Checking repo permissions")
    permission = ReadRepositoryPermission(namespace, repository)
    repository_ref = registry_model.lookup_repository(namespace, repository, kind_filter="image")
    if not permission.can() and not (repository_ref is not None and repository_ref.is_public):
        abort(403)

    logger.debug("Looking up repo image")
    legacy_image = registry_model.get_legacy_image(repository_ref, image_id, store)
    if legacy_image is None:
        abort(404, "Image %(image_id)s not found", issue="unknown-image", image_id=image_id)

    # NOTE: We can not use jsonify here because we are returning a list not an object.
    response = make_response(json.dumps(legacy_image.full_image_id_chain), 200)
    response.headers.extend(headers)
    return response


@v1_bp.route("/images/<image_id>/json", methods=["PUT"])
@process_auth
@extract_namespace_repo_from_session
@check_v1_push_enabled()
@ensure_namespace_enabled
@check_repository_state
@anon_protect
@check_readonly
def put_image_json(namespace, repository, image_id):
    logger.debug("Checking repo permissions")
    permission = ModifyRepositoryPermission(namespace, repository)
    if not permission.can():
        abort(403)

    repository_ref = registry_model.lookup_repository(namespace, repository, kind_filter="image")
    if repository_ref is None:
        abort(403)

    builder = lookup_manifest_builder(
        repository_ref, session.get("manifest_builder"), store, docker_v2_signing_key
    )
    if builder is None:
        abort(400)

    logger.debug("Parsing image JSON")
    try:
        uploaded_metadata = request.data
        uploaded_metadata_string = uploaded_metadata.decode("utf-8")
        data = json.loads(uploaded_metadata_string)
    except ValueError:
        pass

    if not data or not isinstance(data, dict):
        abort(
            400,
            "Invalid JSON for image: %(image_id)s\nJSON: %(json)s",
            issue="invalid-request",
            image_id=image_id,
            json=request.data,
        )

    if "id" not in data:
        abort(
            400,
            "Missing key `id` in JSON for image: %(image_id)s",
            issue="invalid-request",
            image_id=image_id,
        )

    if image_id != data["id"]:
        abort(
            400,
            "JSON data contains invalid id for image: %(image_id)s",
            issue="invalid-request",
            image_id=image_id,
        )

    logger.debug("Looking up repo image")
    location_pref = store.preferred_locations[0]
    username = get_authenticated_user() and get_authenticated_user().username
    layer = builder.start_layer(
        image_id,
        uploaded_metadata_string,
        location_pref,
        username,
        app.config["PUSH_TEMP_TAG_EXPIRATION_SEC"],
    )
    if layer is None:
        abort(
            400,
            "Image %(image_id)s has invalid metadata",
            issue="invalid-request",
            image_id=image_id,
        )

    return make_response("true", 200)
