import base64
import logging

from flask import Blueprint, Response, abort, current_app, request, stream_with_context
from jsonschema import ValidationError, validate

from app import instance_keys
from data.model import InvalidProxyCacheConfigException
from data.model.proxy_cache import get_proxy_cache_config_for_org
from proxy import Proxy, UpstreamRegistryError
from storage.upstreamproxy import UPSTREAM_ACCESS_SCHEMA, UPSTREAM_PROXY_SUBJECT
from util.security.registry_jwt import InvalidBearerTokenException, decode_bearer_token

# yield chunk size in bytes
CHUNK_SIZE = 256 * 1024

logger = logging.getLogger(__name__)
blobstream_bp = Blueprint("blobstream", __name__)


@blobstream_bp.route("/<path:rest>")
def get_upstream_content(rest):
    """
    Fetches the upstream blob and streams it directly to the client. Parses
    the blob information and authentication token from the payload
    provided via the route name. If parsing fails, returns a 401 response.
    If connection to upstream is terminated prematurely, the request is
    aborted with a 502.
    """
    # verify we have enough parts in the request
    parts = rest.split("/")
    if len(parts) < 8:
        logger.error("Malformed upstream proxy URL (too few parts): want >=8, got %s", len(parts))
        abort(401)

    encoded_token = parts[0]
    scheme = parts[1]
    upstream_hostname = parts[2]
    namespace = parts[4]

    # treat everything between namespace and /blobs as a repo name
    repository = "/".join(parts[5:-2])

    # verify we have "v2" and "blobs" at respective places
    if parts[3] != "v2" or parts[-2] != "blobs":
        logger.error("Malformed proxy URL request structure: %s", rest)
        abort(401)

    # we assume that the last entry is a blob SHA digest
    if not parts[-1].startswith("sha256:"):
        logger.error(
            "Malformed URL request, last part does not appear to be a SHA digest: %s",
            rest,
        )
        abort(401)
    blob_sha = parts[-1]

    try:
        token = base64.urlsafe_b64decode(encoded_token)
    except (ValueError, TypeError) as e:
        logger.exception("Could not decode upstream proxy token: %s", e)
        abort(401)

    logger.debug(
        "Got token %s for upstream proxy auth request %s with parts %s",
        token,
        rest,
        parts,
    )

    # decode the token
    try:
        decoded = decode_bearer_token(token, instance_keys, current_app.config)
    except InvalidBearerTokenException as e:
        logger.exception("Invalid token for upstream proxy: %s", e)
        abort(401)

    # verify the token for the upstream proxy
    if decoded["sub"] != UPSTREAM_PROXY_SUBJECT:
        logger.exception("Invalid subject %s for upstream proxy auth token", decoded["sub"])
        abort(401)

    # verify that access matches the scheme
    access = decoded.get("access", {})
    try:
        validate(access, UPSTREAM_ACCESS_SCHEMA)
    except ValidationError as e:
        logger.exception("We should not be minting invalid credentials: %s", access)
        abort(401)

    # and that we only have one access field
    if len(access) != 1:
        logger.exception("We should not be minting invalid credentials: %s", access)
        abort(401)

    # verify that all components from the JWT match the URL parameters
    granted_access = access[0]
    if granted_access["scheme"] != scheme:
        logger.exception(
            "Mismatch in scheme. %s expected, %s found", granted_access["scheme"], scheme
        )
        abort(401)

    if granted_access["hostname"] != upstream_hostname:
        logger.exception(
            "Mismatch in host, %s expected, %s found",
            granted_access["hostname"],
            upstream_hostname,
        )
        abort(401)

    if granted_access["upstream_namespace"] != namespace:
        logger.exception(
            "Mismatch in namespace, %s expected, %s found",
            granted_access["upstream_namespace"],
            namespace,
        )
        abort(401)

    if granted_access["upstream_repository"] != repository:
        logger.exception(
            "Mismatch in repository. %s expected, %s found",
            granted_access["upstream_repository"],
            repository,
        )
        abort(401)

    if granted_access["blob_sha"] != blob_sha:
        logger.exception(
            "Mismatch in blob SHA digest. %s expected, %s found",
            granted_access["blob_sha"],
            blob_sha,
        )
        abort(401)

    # verify upstream credentials
    local_namespace = granted_access["local_namespace"]
    try:
        config = get_proxy_cache_config_for_org(local_namespace)
    except InvalidProxyCacheConfigException as e:
        logger.exception("No proxy cache found for namespace %s: %s", local_namespace, e)
        abort(401)

    # proxy expects that the repo is in the same {namespace}/{repository} format used throughout
    # the proxy cache code, so the token scope matches what the upstream registry expects
    upstream_repo = f"{namespace}/{repository}"

    # try reading the range header if it's provided
    upstream_headers = {}
    range_header = request.headers.get("Range")
    if range_header:
        upstream_headers["Range"] = range_header

    try:
        upstream_resp = Proxy(config, repository=upstream_repo).get_blob(
            blob_sha, additional_headers=upstream_headers
        )
    except UpstreamRegistryError as e:
        logger.exception("Failed to fetch blob from upstream registry: %s", e)
        abort(502)

    def generate():
        """
        Generator function that yields the upstream blob in chunks to
        calling client. If an error occurs, the generator function
        must reraise the exception, otherwise it might get swallowed by
        downstream.
        """
        bytes_sent = 0
        try:
            for chunk in upstream_resp.iter_content(chunk_size=CHUNK_SIZE):
                bytes_sent += len(chunk)
                yield chunk
        except Exception as e:
            logger.exception(
                "Upstream blob broke after %d bytes transferred, digest=%s repo=%s upstream=%s://%s, exception: %s",
                bytes_sent,
                blob_sha,
                upstream_repo,
                scheme,
                upstream_hostname,
                e,
            )
            raise
        finally:
            upstream_resp.close()

    headers = {
        "Docker-Content-Digest": blob_sha,
    }

    # if blob size is known, let the caller know about it
    if "content-length" in upstream_resp.headers:
        headers["Content-Length"] = upstream_resp.headers["content-length"]

    # if we have a content range in response, let the caller know about it
    if "content-range" in upstream_resp.headers:
        headers["Content-Range"] = upstream_resp.headers["content-range"]

    # if the upstream accepts ranges, let the caller know about it
    if "accept-ranges" in upstream_resp.headers:
        headers["Accept-Ranges"] = upstream_resp.headers["accept-ranges"]

    headers["Content-Type"] = upstream_resp.headers.get("content-type", "application/octet-stream")

    # use upstream response code and send it to the client
    return Response(
        stream_with_context(generate()),
        headers=headers,
        status=upstream_resp.status_code,
    )
