import logging
import re

from flask import url_for, request, redirect, Response, abort as flask_abort

from app import storage, app, get_app_url, model_cache
from auth.registry_jwt_auth import process_registry_jwt_auth
from auth.permissions import ReadRepositoryPermission
from data import database
from data.registry_model import registry_model
from data.registry_model.blobuploader import (
    create_blob_upload,
    retrieve_blob_upload_manager,
    complete_when_uploaded,
    BlobUploadSettings,
    BlobUploadException,
    BlobTooLargeException,
    BlobRangeMismatchException,
)
from digest import digest_tools
from endpoints.decorators import (
    anon_protect,
    anon_allowed,
    disallow_for_account_recovery_mode,
    parse_repository_name,
    check_region_blacklisted,
    check_readonly,
)
from endpoints.metrics import image_pulled_bytes
from endpoints.v2 import v2_bp, require_repo_read, require_repo_write, get_input_stream
from endpoints.v2.errors import (
    BlobUnknown,
    BlobUploadInvalid,
    BlobUploadUnknown,
    Unsupported,
    NameUnknown,
    LayerTooLarge,
    InvalidRequest,
    BlobDownloadGeoBlocked,
)
from util.cache import cache_control
from util.names import parse_namespace_repository
from util.request import get_request_ip


logger = logging.getLogger(__name__)

BASE_BLOB_ROUTE = '/<repopath:repository>/blobs/<regex("{0}"):digest>'
BLOB_DIGEST_ROUTE = BASE_BLOB_ROUTE.format(digest_tools.DIGEST_PATTERN)
RANGE_HEADER_REGEX = re.compile(r"^([0-9]+)-([0-9]+)$")
BLOB_CONTENT_TYPE = "application/octet-stream"


@v2_bp.route(BLOB_DIGEST_ROUTE, methods=["HEAD"])
@disallow_for_account_recovery_mode
@parse_repository_name()
@process_registry_jwt_auth(scopes=["pull"])
@require_repo_read
@anon_allowed
@cache_control(max_age=31436000)
def check_blob_exists(namespace_name, repo_name, digest):
    # Find the blob.
    blob = registry_model.get_cached_repo_blob(model_cache, namespace_name, repo_name, digest)
    if blob is None:
        raise BlobUnknown()

    # Build the response headers.
    headers = {
        "Docker-Content-Digest": digest,
        "Content-Length": blob.compressed_size,
        "Content-Type": BLOB_CONTENT_TYPE,
    }

    # If our storage supports range requests, let the client know.
    if storage.get_supports_resumable_downloads(blob.placements):
        headers["Accept-Ranges"] = "bytes"

    # Write the response to the client.
    return Response(headers=headers)


@v2_bp.route(BLOB_DIGEST_ROUTE, methods=["GET"])
@disallow_for_account_recovery_mode
@parse_repository_name()
@process_registry_jwt_auth(scopes=["pull"])
@require_repo_read
@anon_allowed
@check_region_blacklisted(BlobDownloadGeoBlocked)
@cache_control(max_age=31536000)
def download_blob(namespace_name, repo_name, digest):
    # Find the blob.
    blob = registry_model.get_cached_repo_blob(model_cache, namespace_name, repo_name, digest)
    if blob is None:
        raise BlobUnknown()

    # Build the response headers.
    headers = {"Docker-Content-Digest": digest}

    # If our storage supports range requests, let the client know.
    if storage.get_supports_resumable_downloads(blob.placements):
        headers["Accept-Ranges"] = "bytes"

    image_pulled_bytes.labels("v2").inc(blob.compressed_size)

    # Short-circuit by redirecting if the storage supports it.
    path = blob.storage_path
    logger.debug("Looking up the direct download URL for path: %s", path)
    direct_download_url = storage.get_direct_download_url(blob.placements, path, get_request_ip())
    if direct_download_url:
        logger.debug("Returning direct download URL")
        resp = redirect(direct_download_url)
        resp.headers.extend(headers)
        return resp

    # Close the database connection before we stream the download.
    logger.debug("Closing database connection before streaming layer data")
    headers.update(
        {
            "Content-Length": blob.compressed_size,
            "Content-Type": BLOB_CONTENT_TYPE,
        }
    )

    with database.CloseForLongOperation(app.config):
        # Stream the response to the client.
        return Response(
            storage.stream_read(blob.placements, path),
            headers=headers,
        )


def _try_to_mount_blob(repository_ref, mount_blob_digest):
    """
    Attempts to mount a blob requested by the user from another repository.
    """
    logger.debug("Got mount request for blob `%s` into `%s`", mount_blob_digest, repository_ref)
    from_repo = request.args.get("from", None)
    if from_repo is None:
        raise InvalidRequest(message="Missing `from` repository argument")

    # Ensure the user has access to the repository.
    logger.debug(
        "Got mount request for blob `%s` under repository `%s` into `%s`",
        mount_blob_digest,
        from_repo,
        repository_ref,
    )
    from_namespace, from_repo_name = parse_namespace_repository(
        from_repo, app.config["LIBRARY_NAMESPACE"], include_tag=False
    )

    from_repository_ref = registry_model.lookup_repository(from_namespace, from_repo_name)
    if from_repository_ref is None:
        logger.debug("Could not find from repo: `%s/%s`", from_namespace, from_repo_name)
        return None

    # First check permission.
    read_permission = ReadRepositoryPermission(from_namespace, from_repo_name).can()
    if not read_permission:
        # If no direct permission, check if the repostory is public.
        if not from_repository_ref.is_public:
            logger.debug(
                "No permission to mount blob `%s` under repository `%s` into `%s`",
                mount_blob_digest,
                from_repo,
                repository_ref,
            )
            return None

    # Lookup if the mount blob's digest exists in the repository.
    mount_blob = registry_model.get_cached_repo_blob(
        model_cache, from_namespace, from_repo_name, mount_blob_digest
    )
    if mount_blob is None:
        logger.debug("Blob `%s` under repository `%s` not found", mount_blob_digest, from_repo)
        return None

    logger.debug(
        "Mounting blob `%s` under repository `%s` into `%s`",
        mount_blob_digest,
        from_repo,
        repository_ref,
    )

    # Mount the blob into the current repository and return that we've completed the operation.
    expiration_sec = app.config["PUSH_TEMP_TAG_EXPIRATION_SEC"]
    mounted = registry_model.mount_blob_into_repository(mount_blob, repository_ref, expiration_sec)
    if not mounted:
        logger.debug(
            "Could not mount blob `%s` under repository `%s` not found",
            mount_blob_digest,
            from_repo,
        )
        return

    # Return the response for the blob indicating that it was mounted, and including its content
    # digest.
    logger.debug(
        "Mounted blob `%s` under repository `%s` into `%s`",
        mount_blob_digest,
        from_repo,
        repository_ref,
    )

    namespace_name = repository_ref.namespace_name
    repo_name = repository_ref.name

    return Response(
        status=201,
        headers={
            "Docker-Content-Digest": mount_blob_digest,
            "Location": get_app_url()
            + url_for(
                "v2.download_blob",
                repository="%s/%s" % (namespace_name, repo_name),
                digest=mount_blob_digest,
            ),
        },
    )


@v2_bp.route("/<repopath:repository>/blobs/uploads/", methods=["POST"])
@disallow_for_account_recovery_mode
@parse_repository_name()
@process_registry_jwt_auth(scopes=["pull", "push"])
@require_repo_write
@anon_protect
@check_readonly
def start_blob_upload(namespace_name, repo_name):
    repository_ref = registry_model.lookup_repository(namespace_name, repo_name)
    if repository_ref is None:
        raise NameUnknown()

    # Check for mounting of a blob from another repository.
    mount_blob_digest = request.args.get("mount", None)
    if mount_blob_digest is not None:
        response = _try_to_mount_blob(repository_ref, mount_blob_digest)
        if response is not None:
            return response

    # Begin the blob upload process.
    blob_uploader = create_blob_upload(repository_ref, storage, _upload_settings())
    if blob_uploader is None:
        logger.debug("Could not create a blob upload for `%s/%s`", namespace_name, repo_name)
        raise InvalidRequest(message="Unable to start blob upload for unknown repository")

    # Check if the blob will be uploaded now or in followup calls. If the `digest` is given, then
    # the upload will occur as a monolithic chunk in this call. Otherwise, we return a redirect
    # for the client to upload the chunks as distinct operations.
    digest = request.args.get("digest", None)
    if digest is None:
        # Short-circuit because the user will send the blob data in another request.
        return Response(
            status=202,
            headers={
                "Docker-Upload-UUID": blob_uploader.blob_upload_id,
                "Range": _render_range(0),
                "Location": get_app_url()
                + url_for(
                    "v2.upload_chunk",
                    repository="%s/%s" % (namespace_name, repo_name),
                    upload_uuid=blob_uploader.blob_upload_id,
                ),
            },
        )

    # Upload the data sent and commit it to a blob.
    with complete_when_uploaded(blob_uploader):
        _upload_chunk(blob_uploader, digest)

    # Write the response to the client.
    return Response(
        status=201,
        headers={
            "Docker-Content-Digest": digest,
            "Location": get_app_url()
            + url_for(
                "v2.download_blob", repository="%s/%s" % (namespace_name, repo_name), digest=digest
            ),
        },
    )


@v2_bp.route("/<repopath:repository>/blobs/uploads/<upload_uuid>", methods=["GET"])
@disallow_for_account_recovery_mode
@parse_repository_name()
@process_registry_jwt_auth(scopes=["pull"])
@require_repo_write
@anon_protect
def fetch_existing_upload(namespace_name, repo_name, upload_uuid):
    repository_ref = registry_model.lookup_repository(namespace_name, repo_name)
    if repository_ref is None:
        raise NameUnknown()

    uploader = retrieve_blob_upload_manager(
        repository_ref, upload_uuid, storage, _upload_settings()
    )
    if uploader is None:
        raise BlobUploadUnknown()

    return Response(
        status=204,
        headers={
            "Docker-Upload-UUID": upload_uuid,
            "Range": _render_range(
                uploader.blob_upload.byte_count + 1
            ),  # byte ranges are exclusive
        },
    )


@v2_bp.route("/<repopath:repository>/blobs/uploads/<upload_uuid>", methods=["PATCH"])
@disallow_for_account_recovery_mode
@parse_repository_name()
@process_registry_jwt_auth(scopes=["pull", "push"])
@require_repo_write
@anon_protect
@check_readonly
def upload_chunk(namespace_name, repo_name, upload_uuid):
    repository_ref = registry_model.lookup_repository(namespace_name, repo_name)
    if repository_ref is None:
        raise NameUnknown()

    uploader = retrieve_blob_upload_manager(
        repository_ref, upload_uuid, storage, _upload_settings()
    )
    if uploader is None:
        raise BlobUploadUnknown()

    # Upload the chunk for the blob.
    _upload_chunk(uploader)

    # Write the response to the client.
    return Response(
        status=202,
        headers={
            "Location": _current_request_url(),
            "Range": _render_range(uploader.blob_upload.byte_count, with_bytes_prefix=False),
            "Docker-Upload-UUID": upload_uuid,
        },
    )


@v2_bp.route("/<repopath:repository>/blobs/uploads/<upload_uuid>", methods=["PUT"])
@disallow_for_account_recovery_mode
@parse_repository_name()
@process_registry_jwt_auth(scopes=["pull", "push"])
@require_repo_write
@anon_protect
@check_readonly
def monolithic_upload_or_last_chunk(namespace_name, repo_name, upload_uuid):
    # Ensure the digest is present before proceeding.
    digest = request.args.get("digest", None)
    if digest is None:
        raise BlobUploadInvalid(detail={"reason": "Missing digest arg on monolithic upload"})

    # Find the upload.
    repository_ref = registry_model.lookup_repository(namespace_name, repo_name)
    if repository_ref is None:
        raise NameUnknown()

    uploader = retrieve_blob_upload_manager(
        repository_ref, upload_uuid, storage, _upload_settings()
    )
    if uploader is None:
        raise BlobUploadUnknown()

    # Upload the chunk for the blob and commit it once complete.
    with complete_when_uploaded(uploader):
        _upload_chunk(uploader, digest)

    # Write the response to the client.
    return Response(
        status=201,
        headers={
            "Docker-Content-Digest": digest,
            "Location": get_app_url()
            + url_for(
                "v2.download_blob", repository="%s/%s" % (namespace_name, repo_name), digest=digest
            ),
        },
    )


@v2_bp.route("/<repopath:repository>/blobs/uploads/<upload_uuid>", methods=["DELETE"])
@disallow_for_account_recovery_mode
@parse_repository_name()
@process_registry_jwt_auth(scopes=["pull", "push"])
@require_repo_write
@anon_protect
@check_readonly
def cancel_upload(namespace_name, repo_name, upload_uuid):
    repository_ref = registry_model.lookup_repository(namespace_name, repo_name)
    if repository_ref is None:
        raise NameUnknown()

    uploader = retrieve_blob_upload_manager(
        repository_ref, upload_uuid, storage, _upload_settings()
    )
    if uploader is None:
        raise BlobUploadUnknown()

    uploader.cancel_upload()
    return Response(status=204)


@v2_bp.route("/<repopath:repository>/blobs/<digest>", methods=["DELETE"])
@disallow_for_account_recovery_mode
@parse_repository_name()
@process_registry_jwt_auth(scopes=["pull", "push"])
@require_repo_write
@anon_protect
@check_readonly
def delete_digest(namespace_name, repo_name, digest):
    # We do not support deleting arbitrary digests, as they break repo images.
    raise Unsupported()


def _render_range(num_uploaded_bytes, with_bytes_prefix=True):
    """
    Returns a string formatted to be used in the Range header.
    """
    return "{0}0-{1}".format("bytes=" if with_bytes_prefix else "", num_uploaded_bytes - 1)


def _current_request_url():
    return "{0}{1}{2}".format(get_app_url(), request.script_root, request.path)


def _abort_range_not_satisfiable(valid_end, upload_uuid):
    """
    Writes a failure response for scenarios where the registry cannot function with the provided
    range.

    TODO: Unify this with the V2RegistryException class.
    """
    flask_abort(
        Response(
            status=416,
            headers={
                "Location": _current_request_url(),
                "Range": "0-{0}".format(valid_end),
                "Docker-Upload-UUID": upload_uuid,
            },
        )
    )


def _start_offset_and_length(range_header):
    """
    Returns a tuple of the start offset and the length.

    If the range header doesn't exist, defaults to (0, -1). If parsing fails, returns (None, None).
    """
    start_offset, length = 0, -1
    if range_header is not None:
        # Parse the header.
        found = RANGE_HEADER_REGEX.match(range_header)
        if found is None:
            return (None, None)

        # NOTE: Offsets here are *inclusive*.
        start_offset = int(found.group(1))
        end_offset = int(found.group(2))
        length = end_offset - start_offset + 1
        if length < 0:
            return None, None

    return start_offset, length


def _upload_settings():
    """
    Returns the settings for instantiating a blob upload manager.
    """
    expiration_sec = app.config["PUSH_TEMP_TAG_EXPIRATION_SEC"]
    settings = BlobUploadSettings(
        maximum_blob_size=app.config["MAXIMUM_LAYER_SIZE"],
        committed_blob_expiration=expiration_sec,
    )
    return settings


def _upload_chunk(blob_uploader, commit_digest=None):
    """
    Performs uploading of a chunk of data in the current request's stream, via the blob uploader
    given.

    If commit_digest is specified, the upload is committed to a blob once the stream's data has been
    read and stored.
    """
    start_offset, length = _start_offset_and_length(request.headers.get("content-range"))
    if None in {start_offset, length}:
        raise InvalidRequest(message="Invalid range header")

    input_fp = get_input_stream(request)

    try:
        # Upload the data received.
        blob_uploader.upload_chunk(app.config, input_fp, start_offset, length)

        if commit_digest is not None:
            # Commit the upload to a blob.
            return blob_uploader.commit_to_blob(app.config, commit_digest)
    except BlobTooLargeException as ble:
        raise LayerTooLarge(uploaded=ble.uploaded, max_allowed=ble.max_allowed)
    except BlobRangeMismatchException:
        logger.exception("Exception when uploading blob to %s", blob_uploader.blob_upload_id)
        _abort_range_not_satisfiable(
            blob_uploader.blob_upload.byte_count, blob_uploader.blob_upload_id
        )
    except BlobUploadException:
        logger.exception("Exception when uploading blob to %s", blob_uploader.blob_upload_id)
        raise BlobUploadInvalid()
