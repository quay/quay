import logging
import base64
import urllib.request, urllib.parse, urllib.error

from urllib.parse import urlparse
from flask import abort, request
from jsonschema import validate, ValidationError

from util.security.registry_jwt import (
    generate_bearer_token,
    decode_bearer_token,
    InvalidBearerTokenException,
)

logger = logging.getLogger(__name__)


PROXY_STORAGE_MAX_LIFETIME_S = 30  # Seconds
STORAGE_PROXY_SUBJECT = "storageproxy"
STORAGE_PROXY_ACCESS_TYPE = "storageproxy"

ACCESS_SCHEMA = {
    "type": "array",
    "description": "List of access granted to the subject",
    "items": {
        "type": "object",
        "required": ["type", "scheme", "host", "uri",],
        "properties": {
            "type": {
                "type": "string",
                "description": "We only allow storage proxy permissions",
                "enum": ["storageproxy",],
            },
            "scheme": {
                "type": "string",
                "description": "The scheme for the storage URL being proxied",
            },
            "host": {
                "type": "string",
                "description": "The hostname for the storage URL being proxied",
            },
            "uri": {
                "type": "string",
                "description": "The URI path for the storage URL being proxied",
            },
        },
    },
}


class DownloadProxy(object):
    """
    Helper class to enable proxying of direct download URLs for storage via the registry's local
    NGINX.
    """

    def __init__(self, app, instance_keys):
        self.app = app
        self.instance_keys = instance_keys

        app.add_url_rule("/_storage_proxy_auth", "_storage_proxy_auth", self._validate_proxy_url)

    def proxy_download_url(self, download_url):
        """
        Returns a URL to proxy the specified blob download URL.
        """
        # Parse the URL to be downloaded into its components (host, path, scheme).
        parsed = urlparse(download_url)

        path = parsed.path
        if parsed.query:
            path = path + "?" + parsed.query

        if path.startswith("/"):
            path = path[1:]

        access = {
            "type": STORAGE_PROXY_ACCESS_TYPE,
            "uri": path,
            "host": parsed.netloc,
            "scheme": parsed.scheme,
        }

        # Generate a JWT that signs access to this URL. This JWT will be passed back to the registry
        # code when the download commences. Note that we don't add any context here, as it isn't
        # needed.
        server_hostname = self.app.config["SERVER_HOSTNAME"]
        token = generate_bearer_token(
            server_hostname,
            STORAGE_PROXY_SUBJECT,
            {},
            [access],
            PROXY_STORAGE_MAX_LIFETIME_S,
            self.instance_keys,
        )

        url_scheme = self.app.config["PREFERRED_URL_SCHEME"]
        server_hostname = self.app.config["SERVER_HOSTNAME"]

        # The proxy path is of the form:
        # http(s)://registry_server/_storage_proxy/{token}/{scheme}/{hostname}/rest/of/path/here
        encoded_token = base64.urlsafe_b64encode(token)
        proxy_url = "%s://%s/_storage_proxy/%s/%s/%s/%s" % (
            url_scheme,
            server_hostname,
            encoded_token.decode("ascii"),
            parsed.scheme,
            parsed.netloc,
            path,
        )
        logger.debug("Proxying via URL %s", proxy_url)
        return proxy_url

    def _validate_proxy_url(self):
        original_uri = request.headers.get("X-Original-URI", None)
        if not original_uri:
            logger.error("Missing original URI: %s", request.headers)
            abort(401)

        if not original_uri.startswith("/_storage_proxy/"):
            logger.error("Unknown storage proxy path: %s", original_uri)
            abort(401)

        # The proxy path is of the form:
        # /_storage_proxy/{token}/{scheme}/{hostname}/rest/of/path/here
        without_prefix = original_uri[len("/_storage_proxy/") :]
        parts = without_prefix.split("/", 3)
        if len(parts) != 4:
            logger.error(
                "Invalid storage proxy path (found %s parts): %s", len(parts), without_prefix
            )
            abort(401)

        encoded_token, scheme, host, uri = parts

        try:
            token = base64.urlsafe_b64decode(encoded_token)
        except ValueError:
            logger.exception("Could not decode proxy token")
            abort(401)
        except TypeError:
            logger.exception("Could not decode proxy token")
            abort(401)

        logger.debug(
            "Got token %s for storage proxy auth request %s with parts %s",
            token,
            original_uri,
            parts,
        )

        # Decode the bearer token.
        try:
            decoded = decode_bearer_token(token, self.instance_keys, self.app.config)
        except InvalidBearerTokenException:
            logger.exception("Invalid token for storage proxy")
            abort(401)

        # Ensure it is for the proxy.
        if decoded["sub"] != STORAGE_PROXY_SUBJECT:
            logger.exception("Invalid subject %s for storage proxy auth", decoded["subject"])
            abort(401)

        # Validate that the access matches the token format.
        access = decoded.get("access", {})
        try:
            validate(access, ACCESS_SCHEMA)
        except ValidationError:
            logger.exception("We should not be minting invalid credentials: %s", access)
            abort(401)

        # For now, we only expect a single access credential.
        if len(access) != 1:
            logger.exception("We should not be minting invalid credentials: %s", access)
            abort(401)

        # Ensure the signed access matches the requested URL's pieces.
        granted_access = access[0]
        if granted_access["scheme"] != scheme:
            logger.exception(
                "Mismatch in scheme. %s expected, %s found", granted_access["scheme"], scheme
            )
            abort(401)

        if granted_access["host"] != host:
            logger.exception(
                "Mismatch in host. %s expected, %s found", granted_access["host"], host
            )
            abort(401)

        if granted_access["uri"] != uri:
            logger.exception("Mismatch in uri. %s expected, %s found", granted_access["uri"], uri)
            abort(401)

        return "OK"
