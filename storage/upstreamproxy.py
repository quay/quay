import base64
import logging

from flask import Flask

from util.security.registry_jwt import (
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
