"""
The proxy module provides the means to proxy images from other registry instances.
Registries following the distribution spec are supported.
"""
from __future__ import annotations

import re
from urllib.parse import urlencode

import requests
from requests.exceptions import RequestException

from app import model_cache
from data.cache import cache_key
from data.database import ProxyCacheConfig

WWW_AUTHENTICATE_REGEX = re.compile(r'(\w+)[=] ?"?([^",]+)"?')
TOKEN_VALIDITY_LIFETIME_S = 60 * 60  # 1 hour, in seconds - Quay's default
TOKEN_RENEWAL_THRESHOLD = 10  # interval (in seconds) when to renew auth token

REGISTRY_URLS = {"docker.io": "registry-1.docker.io"}


class UpstreamRegistryError(Exception):
    def __init__(self, detail):
        msg = (
            "the requested image may not exist in the upstream registry, or the configured "
            f"Quay organization credentials have insufficient rights to access it ({detail})"
        )
        super().__init__(msg)


def parse_www_auth(value: str) -> dict[str, str]:
    """
    Parses WWW-Authenticate parameters and returns a dict of key=val.
    See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/WWW-Authenticate
    for details.
    This parser is *not* fully compliant with RFC 7235, notably it does not support
    multiple challenges.
    """
    scheme = value.split(" ", 1)[0]
    matches = WWW_AUTHENTICATE_REGEX.findall(value)
    parsed = dict(matches)
    if scheme:
        parsed["scheme"] = scheme
    return parsed


class Proxy:
    # TODO: replace self._repo with a parameter on each public method instead
    def __init__(
        self, config: ProxyCacheConfig, repository: str | None = None, validation: bool = False
    ):
        self._config = config
        self._validation = validation

        hostname = REGISTRY_URLS.get(
            config.upstream_registry_hostname,
            config.upstream_registry_hostname,
        )
        url = f"https://{hostname}"
        if config.insecure:
            url = f"http://{hostname}"

        self.base_url = url
        self._session = requests.Session()
        self._repo = repository
        self._authorize(self._credentials(), force_renewal=self._validation)
        # flag used for validating Proxy cache config before saving to db

    def get_manifest(
        self, image_ref: str, media_types: list[str] | None = None
    ) -> tuple[bytes, str | None]:
        url = f"{self.base_url}/v2/{self._repo}/manifests/{image_ref}"
        headers = {}
        if media_types is not None:
            headers["Accept"] = ", ".join(media_types)
        resp = self.get(url, headers=headers)
        raw_manifest = resp.content
        content_type = resp.headers.get("content-type")
        return raw_manifest, content_type

    def manifest_exists(self, image_ref: str, media_types: list[str] | None = None) -> str | None:
        """
        Returns the manifest digest.

        Looks for the digest in the docker-content-digest header. If not
        present in the response, parses the manifest then calculate the digest.

        If the manifest does not exist or the upstream registry errors, raises
        an UpstreamRegistryError exception.
        """
        url = f"{self.base_url}/v2/{self._repo}/manifests/{image_ref}"
        headers = {}
        if media_types is not None:
            headers["Accept"] = ", ".join(media_types)
        resp = self.head(url, headers=headers, allow_redirects=True)
        return resp.headers.get("docker-content-digest")

    def get_blob(self, digest: str):
        url = f"{self.base_url}/v2/{self._repo}/blobs/{digest}"
        resp = self.get(
            url,
            headers={
                "Accept-Encoding": "identity",
            },
            allow_redirects=True,
            stream=True,
        )
        return resp

    def blob_exists(self, digest: str):
        url = f"{self.base_url}/v2/{self._repo}/blobs/{digest}"
        resp = self.head(url, allow_redirects=True)
        return {
            "response": resp.text,
            "status": resp.status_code,
            "headers": dict(resp.headers),
        }

    def get(self, *args, **kwargs) -> requests.Response:
        """
        Wrapper for session.get for renewing auth tokens and retrying requests in case of 401.
        """
        return self._request(self._session.get, *args, **kwargs)

    def head(self, *args, **kwargs) -> requests.Response:
        """
        Wrapper for session.head for renewing auth tokens and retrying requests in case of 401.
        """
        return self._request(self._session.head, *args, **kwargs)

    def _request(self, request_func, *args, **kwargs) -> requests.Response:
        resp = self._safe_request(request_func, *args, **kwargs)
        if resp.status_code == 401:
            self._authorize(self._credentials(), force_renewal=True)
            resp = self._safe_request(request_func, *args, **kwargs)
        # allow 401 for anonymous pulls when validating proxy cache config
        if resp.status_code == 401 and self._validation:
            return resp
        if not resp.ok:
            raise UpstreamRegistryError(resp.status_code)
        return resp

    def _safe_request(self, request_func, *args, **kwargs):
        try:
            return request_func(*args, **kwargs)
        except (RequestException, ConnectionError) as e:
            raise UpstreamRegistryError(str(e))

    def _credentials(self) -> tuple[str, str] | None:
        auth = None
        username = self._config.upstream_registry_username
        password = self._config.upstream_registry_password
        if username is not None and password is not None:
            auth = (
                (username, password)
                if isinstance(username, str) and isinstance(password, str)
                else (username.decrypt(), password.decrypt())
            )
        return auth

    def _authorize(self, auth: tuple[str, str] | None = None, force_renewal: bool = False) -> None:
        raw_token = model_cache.retrieve(self._cache_key(), lambda: None)
        if raw_token is not None and not force_renewal:
            token = raw_token["token"]
            if isinstance(token, bytes):
                token = token.decode("ascii")
            self._session.headers["Authorization"] = f"Bearer {token}"
            return

        if force_renewal:
            self._session.headers.pop("Authorization", None)

        # the /v2/ endpoint returns 401 when the client is not authorized.
        # if we get 200, there's no need to proceed.
        resp = self._safe_request(self._session.get, f"{self.base_url}/v2/")
        if resp.status_code == 200:
            return

        www_auth = parse_www_auth(resp.headers.get("www-authenticate", ""))
        scheme = www_auth.get("scheme")
        service = www_auth.get("service")
        realm = www_auth.get("realm")

        if str(scheme).lower() == "basic" and auth is not None:
            # attach basic auth header to session
            requests.auth.HTTPBasicAuth(auth[0], auth[1])(self._session)
            return

        params = {}
        if service is not None:
            params["service"] = service
        if self._repo is not None:
            params["scope"] = f"repository:{self._repo}:pull"
        query_string = urlencode(params)

        auth_url = f"{realm}"
        if query_string != "":
            auth_url = f"{auth_url}?{query_string}"

        basic_auth = None
        if auth is not None:
            basic_auth = requests.auth.HTTPBasicAuth(auth[0], auth[1])
        resp = self._safe_request(self._session.get, auth_url, auth=basic_auth)

        # ignore fetching a token when validating proxy cache config to allow anonymous pulls from registries,
        # since the repo name is not known during the initial proxy configuration
        if resp.status_code == 401 and auth is None and self._repo is None:
            return

        if not resp.ok:
            raise UpstreamRegistryError(
                f"Failed to get token from: '{realm}', with status code: {resp.status_code}"
            )

        resp_json = resp.json()
        token = resp_json.get("token")
        if token is None:
            # For OAuth2.0 compatability, "access_token" can also used and is equivalent to "token" "
            # https://docs.docker.com/registry/spec/auth/token/#token-response-fields
            token = resp_json.get("access_token")
            if token is None:
                raise UpstreamRegistryError(
                    f"Failed to get authentication token from: '{realm}' response"
                )

        # our cached token will expire a few seconds (TOKEN_RENEWAL_THRESHOLD)
        # before the actual token expiration.
        # we do this so that we can renew the token before actually hitting
        # any 401s, to save some http requests.
        expires_in = resp_json.get("expires_in", TOKEN_VALIDITY_LIFETIME_S)
        expires_in -= TOKEN_RENEWAL_THRESHOLD
        model_cache.retrieve(self._cache_key(expires_in), lambda: {"token": token})
        self._session.headers["Authorization"] = f"{scheme} {token}"

    def _cache_key(self, expires_in=TOKEN_VALIDITY_LIFETIME_S):
        key = cache_key.for_upstream_registry_token(
            self._config.organization.username,
            self._config.upstream_registry,
            self._repo,
            f"{expires_in}s",
        )
        return key
