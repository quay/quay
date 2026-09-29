import base64
import logging

from flask import Flask, abort, make_response, request
from jsonschema import ValidationError, validate

from util.security.registry_jwt import (
    InvalidBearerTokenException,
    decode_bearer_token,
    generate_bearer_token,
)

logger = logging.getLogger(__name__)

# token is valid for up to 10 minutes after issuing
UPSTREAM_PROXY_MAX_LIFETIME_S = 600
UPSTREAM_PROXY_SUBJECT = "upstreamproxy"
UPSTREAM_PROXY_ACCESS_TYPE = "upstreamproxy"

UPSTREAM_ACCESS_SCHEMA = {
    "type": "array",
    "description": "List of access granted to the subject",
    "items": {
        "type": "object",
        "required": [
            "type",
            "scheme",
            "hostname",
            "local_namespace",
            "upstream_namespace",
            "upstream_repository",
            "blob_sha",
        ],
        "properties": {
            "type": {
                "type": "string",
                "description": "We only allow upstream proxy permissions",
                "enum": [
                    "upstreamproxy",
                ],
            },
            "scheme": {
                "type": "string",
                "description": "Upstream registry URL scheme",
            },
            "hostname": {
                "type": "string",
                "description": "Upstream registry hostname",
            },
            "local_namespace": {
                "type": "string",
                "description": "Local namespace where proxy configuration lives",
            },
            "upstream_namespace": {
                "type": "string",
                "description": "Upstream registry namespace",
            },
            "upstream_repository": {
                "type": "string",
                "description": "Upstream registry repository",
            },
            "blob_sha": {
                "type": "string",
                "description": "Blob SHA digest to download",
            },
        },
    },
}


class UpstreamProxy(object):
    """
    Helper class to enable proxying of upstream blobs through Quay's own nginx until the blob
    is stored in local objest storage.
    """

    def __init__(self, app: Flask, instance_keys):
        self.app = app
        self.instance_keys = instance_keys

        app.add_url_rule(
            "/_upstream_proxy_auth", "_upstream_proxy_auth", self._validate_upstream_proxy_auth
        )

    def create_upstream_proxy_url(
        self,
        scheme,
        hostname,
        local_namespace,
        upstream_namespace,
        upstream_repository,
        blob_sha_digest,
    ):
        """
        Returns the download URL for the blob proxied from upstream registry.
        """
        # if we don't provide namespace, assume the upstream registry is using "library"
        if upstream_namespace == "":
            upstream_namespace = "library"

        access = {
            "type": UPSTREAM_PROXY_ACCESS_TYPE,
            "scheme": scheme,
            "hostname": hostname,
            "local_namespace": local_namespace,
            "upstream_namespace": upstream_namespace,
            "upstream_repository": upstream_repository,
            "blob_sha": blob_sha_digest,
        }

        server_hostname = self.app.config["SERVER_HOSTNAME"]

        # generate a JWT to be passed to the registry
        token = generate_bearer_token(
            server_hostname,
            UPSTREAM_PROXY_SUBJECT,
            {},
            [access],
            UPSTREAM_PROXY_MAX_LIFETIME_S,
            self.instance_keys,
        )

        url_scheme = self.app.config["PREFERRED_URL_SCHEME"]

        # proxy path is of the form
        # http(s)://REGISTRY_HOSTNAME/_upstream_proxy/{JWT}/{scheme}/{upstream_hostname}/v2/{namespace}/{repo}/blobs/{blob_sha_digest}
        encoded_token = base64.urlsafe_b64encode(bytes(token, "utf-8"))
        proxy_url = f"{url_scheme}://{server_hostname}/_upstream_proxy/{encoded_token.decode("ascii")}/{scheme}/{hostname}/v2/{upstream_namespace}/{upstream_repository}/blobs/{blob_sha_digest}"

        logger.debug("Proxying upstream blob via url %s", proxy_url)

        return proxy_url

    def _validate_upstream_proxy_auth(self):
        """
        Validates the Quay JWT for an upstream proxy request and returns the upstream registry
        bearer token as X-Upstream-Auth so nginx can inject it into the proxy_pass call.
        """
        from data.model import InvalidProxyCacheConfigException
        from data.model.proxy_cache import get_proxy_cache_config_for_org
        from proxy import Proxy, UpstreamRegistryError

        original_uri = request.headers.get("X-Original-URI", None)
        if not original_uri:
            logger.error("Missing X-Original-URI header: %s", request.headers)
            abort(401)

        if not original_uri.startswith("/_upstream_proxy/"):
            logger.error("Unknown upstream proxy path %s", original_uri)
            abort(401)

        # The proxy path is of the form
        # /_upstream_proxy/{token}/{scheme}/{upstream_hostname}/v2/{namespace}/{repository}/blobs/{blob_sha_digest}
        without_prefix = original_uri.removeprefix("/_upstream_proxy/")

        # extract individual parts from the url
        parts = without_prefix.split("/")

        # minimum amount of components is 8, this includes "v2" and "blobs"
        if len(parts) < 8:
            logger.error(
                "Malformed upstream proxy URL (too few parts): want >8, got %s", len(parts)
            )
            abort(401)

        encoded_token = parts[0]
        scheme = parts[1]
        upstream_hostname = parts[2]
        namespace = parts[4]

        # treat everything in between as repository name
        repository = "/".join(parts[5:-2])

        # verify that we have "v2" and "blobs" in proper places
        if parts[3] != "v2" or parts[-2] != "blobs":
            logger.error("Malformed proxy URL request structure: %s", original_uri)
            abort(401)

        # we assume that the last entry is a blob SHA digest
        if not parts[-1].startswith("sha256:"):
            logger.error(
                "Malformed URL request, last part does not appear to be a SHA digest: %s",
                original_uri,
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
            original_uri,
            parts,
        )

        # decode the bearer token
        try:
            decoded = decode_bearer_token(token, self.instance_keys, self.app.config)
        except InvalidBearerTokenException as e:
            logger.exception("Invalid token for upstream proxy: %s", e)
            abort(401)

        # verify the token is for the upstream proxy
        if decoded["sub"] != UPSTREAM_PROXY_SUBJECT:
            logger.exception("Invalid subject %s for upstream proxy auth token", decoded["sub"])
            abort(401)

        # verify that access matches the schema
        access = decoded.get("access", {})
        try:
            validate(access, UPSTREAM_ACCESS_SCHEMA)
        except ValidationError as e:
            logger.exception("We should not be minting invalid credentials: %s", access)
            abort(401)

        # and that we have only 1 access field
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
                "Mismatch in host. %s expected, %s found",
                granted_access["hostname"],
                upstream_hostname,
            )
            abort(401)

        if granted_access["upstream_namespace"] != namespace:
            logger.exception(
                "Mismatch in namespace. %s expected, %s found",
                granted_access["upstream_namespace"],
                namespace,
            )
            abort(401)

        if granted_access["upstream_repository"] != repository:
            logger.exception(
                "Mismatch in repository. %s expected, %s found",
                granted_access["repository"],
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

        # we now need to verify upstream credentials so we can inject it into the response for nginx
        local_namespace = granted_access["local_namespace"]
        try:
            config = get_proxy_cache_config_for_org(local_namespace)
        except InvalidProxyCacheConfigException as e:
            logger.exception("No proxy cache config found for namespace %s: %s", namespace, e)
            abort(401)

        # proxy expects that the repo is in the same {namespace}/{repository} format used throughout
        # the proxy cache code, so the token scope matches what the upstream registry expects
        upstream_repo = f"{namespace}/{repository}"
        try:
            proxy = Proxy(config, repository=upstream_repo)
            proxy._ensure_authorized()
        except UpstreamRegistryError as e:
            logger.exception("Failed to authorize with the upstream registry: %s", e)
            abort(401)

        # return the full authorized header to nginx so it can be easily injected into the upstream
        # request
        upstream_auth = proxy._session.headers.get("Authorization", "")

        response = make_response("OK", 200)
        response.headers["X-Upstream-Auth"] = upstream_auth
        return response
