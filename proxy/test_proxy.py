import json
import unittest
from datetime import datetime
from unittest import mock

import pytest
from httmock import HTTMock, response, urlmatch

from app import app
from data.cache.impl import InMemoryDataModelCache
from data.database import ProxyCacheConfig, User
from data.encryption import FieldEncrypter
from data.fields import LazyEncryptedValue
from proxy import Proxy, UpstreamRegistryError, parse_www_auth

ANONYMOUS_TOKEN = "anonymous-token"
USER_TOKEN = "user-token"
TAG = "14"
TAG_404 = "666"
TAG_NO_DIGEST = "11"
DIGEST = "sha256:2e7d2c03a9507ae265ecf5b5356885a53393a2029d241394997265a1a25aefc6"
DIGEST_404 = "sha256:3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d"


class TestWWWAuthParser(unittest.TestCase):
    realm = "https://auth.docker.io/token"
    service = "registry.docker.io"

    def test_parse_scheme_bearer(self):
        scheme = "Bearer"
        header = f'{scheme} realm="{self.realm}",service="{self.service}"'
        parsed = parse_www_auth(header)
        self.assertEqual(parsed["scheme"], scheme)

    def test_parse_scheme_basic(self):
        scheme = "Basic"
        header = f'{scheme} realm="{self.realm}",service="{self.service}"'
        parsed = parse_www_auth(header)
        self.assertEqual(parsed["scheme"], scheme)

    def test_parse_realm(self):
        header = f'Bearer realm="{self.realm}",service="{self.service}"'
        parsed = parse_www_auth(header)
        self.assertEqual(parsed["realm"], self.realm)

    def test_parse_service(self):
        header = f'Bearer realm="{self.realm}",service="{self.service}"'
        parsed = parse_www_auth(header)
        self.assertEqual(parsed["service"], self.service)

    def test_parse_empty(self):
        parsed = parse_www_auth("")
        self.assertEqual(parsed, {})


WWW_AUTHENTICATE_BEARER = 'Bearer realm="https://auth.docker.io/token",service="registry.docker.io"'


def docker_registry_mock_401(url, request):
    headers = {"www-authenticate": WWW_AUTHENTICATE_BEARER}
    content = {
        "errors": [
            {
                "code": "UNAUTHORIZED",
                "message": "authentication required",
                "detail": None,
            }
        ]
    }
    return response(401, content, headers, request=request)


def docker_registry_mock_401_basic_auth(url, request):
    basic_auth = 'Basic realm="https://auth.docker.io/token",service="registry.docker.io"'
    headers = {
        "www-authenticate": basic_auth,
    }
    content = {
        "errors": [
            {
                "code": "UNAUTHORIZED",
                "message": "authentication required",
                "detail": None,
            }
        ]
    }
    return response(401, content, headers, request=request)


def docker_auth_mock(url, request):
    token = ANONYMOUS_TOKEN
    auth_header = request.headers.get("Authorization", None)
    if auth_header is not None:
        token = USER_TOKEN

    content = {
        "token": token,
        "access_token": "access-token",
        "expires_in": 300,
        "issued_at": str(datetime.utcnow().isoformat() + "Z"),
    }
    return response(200, content, request=request)


def docker_registry_manifest(url, request):
    content = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        "config": {
            "mediaType": "application/vnd.docker.container.image.v1+json",
            "size": 10231,
            "digest": "sha256:07e2ee723e2d9c8c141137bf9de1037fd2494248e13da2805a95ad840f61dd6c",
        },
        "layers": [
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 31357624,
                "digest": "sha256:a2abf6c4d29d43a4bf9fbb769f524d0fb36a2edab49819c1bf3e76f409f953ea",
            }
        ],
    }
    headers = {
        "docker-content-digest": DIGEST,
        "content-type": "application/vnd.docker.distribution.manifest.v2+json",
    }
    return response(200, content, headers, request=request)


def docker_registry_manifest_404(url, request):
    content = {
        "errors": [
            {
                "code": "MANIFEST_UNKNOWN",
                "message": "manifest unknown",
                "detail": f"unknown tag={TAG_404}",
            }
        ]
    }
    return response(404, content, request=request)


def docker_registry_manifest_no_digest(url, request):
    return response(200, "", request=request)


def docker_registry_blob(url, request):
    return response(200, request=request)


def docker_registry_blob_404(url, request):
    content = {
        "errors": [
            {"code": "BLOB_UNKNOWN", "message": "blob unknown to registry", "detail": DIGEST_404}
        ]
    }
    return response(404, content, request=request)


@urlmatch(netloc=r"(.*\.)?docker\.io")
def docker_registry_mock(url, request):
    if url.netloc == "registry-1.docker.io":
        if url.path == "/v2" or url.path == "/v2/":
            return docker_registry_mock_401(url, request)

        elif url.path == f"/v2/library/postgres/manifests/{TAG}":
            return docker_registry_manifest(url, request)

        elif url.path == f"/v2/library/postgres/manifests/{TAG_404}":
            return docker_registry_manifest_404(url, request)

        elif url.path == f"/v2/library/postgres/manifests/{TAG_NO_DIGEST}":
            return docker_registry_manifest_no_digest(url, request)

        elif url.path == f"/v2/library/postgres/blobs/{DIGEST}":
            return docker_registry_blob(url, request)

        elif f"/v2/library/postgres/blobs/{DIGEST_404}" == url.path:
            return docker_registry_blob_404(url, request)

    elif url.netloc == "auth.docker.io":
        return docker_auth_mock(url, request)

    msg = f"Oops, this endpoint isn't mocked. requested {url.netloc}/{url.path.lstrip('/')}"
    content = {"errors": [{"message": msg}]}
    return response(404, content, request=request)


class TestProxy(unittest.TestCase):
    def setUp(self):
        registry_url = "docker.io"

        self.config = ProxyCacheConfig(
            upstream_registry=registry_url,
            organization=User(username="cache-org", organization=True),
        )

        encrypter = FieldEncrypter(app.config.get("DATABASE_SECRET_KEY"))
        username_field = ProxyCacheConfig.upstream_registry_username
        password_field = ProxyCacheConfig.upstream_registry_password
        user = LazyEncryptedValue(
            encrypter.encrypt_value("user", field_max_length=username_field.max_length),
            username_field,
        )
        password = LazyEncryptedValue(
            encrypter.encrypt_value("pass", field_max_length=password_field.max_length),
            password_field,
        )

        self.auth_config = ProxyCacheConfig(
            upstream_registry=registry_url,
            upstream_registry_username=user,
            upstream_registry_password=password,
            organization=User(username="cache-org", organization=True),
        )

    def test_anonymous_auth_sets_session_token(self):
        with HTTMock(docker_registry_mock):
            proxy = Proxy(self.config, "library/postgres")

        self.assertEqual(proxy._session.headers.get("Authorization"), f"Bearer {ANONYMOUS_TOKEN}")

    def test_auth_with_user_creds_set_session_token(self):
        cache_config = app.config.get("DATA_MODEL_CACHE_CONFIG", {})
        cache = InMemoryDataModelCache(cache_config)
        with mock.patch("proxy.model_cache", cache):
            with HTTMock(docker_registry_mock):
                proxy = Proxy(self.auth_config, "library/postgres")

        self.assertEqual(proxy._session.headers.get("Authorization"), f"Bearer {USER_TOKEN}")

    def test_auth_with_user_creds_and_basic_auth(self):
        @urlmatch(netloc=r"(.*\.)?docker\.io")
        def docker_basic_auth_mock(url, request):
            return docker_registry_mock_401_basic_auth(url, request)

        cache_mock = mock.MagicMock()
        cache_mock.retrieve.return_value = None
        with mock.patch("proxy.model_cache", cache_mock):
            with HTTMock(docker_basic_auth_mock):
                proxy = Proxy(self.auth_config, "library/postgres")

        self.assertIn("Basic", proxy._session.headers.get("Authorization"))

    def test_auth_caches_session_token(self):
        cache_mock = mock.MagicMock()
        cache_mock.retrieve.return_value = None
        with mock.patch("proxy.model_cache", cache_mock):
            with HTTMock(docker_registry_mock):
                proxy = Proxy(self.auth_config, "library/postgres")

        expected_count = 2  # one to check, another to cache
        self.assertEqual(cache_mock.retrieve.call_count, expected_count)
        self.assertIn("Authorization", proxy._session.headers)

    def test_auth_uses_cached_token(self):
        cache_mock = mock.MagicMock()
        token = "this-token"
        cache_mock.retrieve.return_value = {
            "token": token,
            "issued_at": datetime.timestamp(datetime.utcnow()),
            "expires_in": 300,
        }
        with mock.patch("proxy.model_cache", cache_mock):
            with HTTMock(docker_registry_mock):
                proxy = Proxy(self.auth_config, "library/postgres")

        expected_count = 1  # value already cached
        self.assertEqual(cache_mock.retrieve.call_count, expected_count)
        self.assertIn(token, proxy._session.headers["Authorization"])

    def test_get_manifest(self):
        with HTTMock(docker_registry_mock):
            proxy = Proxy(self.config, "library/postgres")
            raw_manifest, _ = proxy.get_manifest(image_ref=TAG)

        manifest = json.loads(raw_manifest)
        self.assertEqual(list(manifest.keys()), ["schemaVersion", "mediaType", "config", "layers"])

    def test_get_manifest_404(self):
        with HTTMock(docker_registry_mock):
            proxy = Proxy(self.config, "library/postgres")
            with pytest.raises(UpstreamRegistryError) as excinfo:
                proxy.get_manifest(image_ref=TAG_404)
        self.assertIn("404", str(excinfo.value))

    def test_session_request_wrapper_retries_request_on_failed_auth(self):
        with HTTMock(docker_registry_mock):
            proxy = Proxy(self.config, "library/postgres")

        manifests_url = "https://registry-1.docker.io/v2/library/postgres/manifests/14"
        manifests_headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}

        class UpstreamMock:
            auth_calls = 0
            get_calls = 0

            def get_mock(self, *args, **kwargs):
                m = mock.MagicMock(status_code=200)
                if self.get_calls == 0:
                    m = mock.MagicMock(status_code=401)
                self.get_calls += 1
                return m

            def auth_mock(self, *args, **kwargs):
                self.auth_calls += 1
                return mock.MagicMock(status_code=200)

        upstream_mock = UpstreamMock()

        get_mock = upstream_mock.get_mock
        auth_mock = upstream_mock.get_mock
        proxy._authorize = upstream_mock.auth_mock
        proxy._request(
            get_mock,
            manifests_url,
            headers=manifests_headers,
        )
        self.assertEqual(upstream_mock.get_calls, 2)
        self.assertEqual(upstream_mock.auth_calls, 1)

    def test_manifest_exists(self):
        with HTTMock(docker_registry_mock):
            proxy = Proxy(self.config, "library/postgres")
            digest = proxy.manifest_exists(image_ref=TAG)
        self.assertNotEqual(digest, "")
        self.assertNotEqual(digest, None)

    def test_manifest_exists_404(self):
        with HTTMock(docker_registry_mock):
            proxy = Proxy(self.config, "library/postgres")
            with pytest.raises(UpstreamRegistryError) as excinfo:
                proxy.manifest_exists(image_ref=TAG_404)

        self.assertIn("404", str(excinfo.value))

    def test_manifest_exists_without_digest_header(self):
        with HTTMock(docker_registry_mock):
            proxy = Proxy(self.config, "library/postgres")
            digest = proxy.manifest_exists(image_ref=TAG_NO_DIGEST)
        self.assertIsNone(digest, None)

    def test_get_blob(self):
        with HTTMock(docker_registry_mock):
            proxy = Proxy(self.config, "library/postgres")
            try:
                proxy.get_blob(digest=DIGEST)
            except UpstreamRegistryError as e:
                pytest.fail(f"unexpected UpstreamRegistryError {e}")

    def test_get_blob_404(self):
        with HTTMock(docker_registry_mock):
            proxy = Proxy(self.config, "library/postgres")
            with pytest.raises(UpstreamRegistryError) as excinfo:
                proxy.get_blob(digest=DIGEST_404)

        self.assertIn("404", str(excinfo.value))

    def test_blob_exists(self):
        with HTTMock(docker_registry_mock):
            proxy = Proxy(self.config, "library/postgres")
            resp = proxy.blob_exists(digest=DIGEST)

        self.assertEqual(resp["status"], 200)

    def test_blob_exists_404(self):
        with HTTMock(docker_registry_mock):
            proxy = Proxy(self.config, "library/postgres")
            with pytest.raises(UpstreamRegistryError) as excinfo:
                proxy.blob_exists(digest=DIGEST_404)
        self.assertIn("404", str(excinfo.value))
