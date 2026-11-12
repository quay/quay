import base64
import importlib
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from endpoints.test.shared import toggle_feature
from storage.upstreamproxy import UpstreamProxy
from test.fixtures import *

TEST_SERVER_HOSTNAME = "quay.test"
TEST_SCHEME = "https"
TEST_UPSTREAM_HOSTNAME = "registry-1.docker.io"
TEST_LOCAL_NAMESPACE = "myorg"
TEST_UPSTREAM_NAMESPACE = "library"
TEST_UPSTREAM_REPO = "fedora"
TEST_DIGEST = "sha256:" + "a" * 64
BAD_TOKEN = base64.urlsafe_b64encode(b"this-is-not-a-jwt").decode("ascii")


@pytest.fixture
def real_instance_keys(initialized_db):
    from app import instance_keys

    return instance_keys


@pytest.fixture
def url_proxy(app, real_instance_keys):
    """
    Helper proxy that allows us to mint valid test URLs.
    """
    app.config["SERVER_HOSTNAME"] = TEST_SERVER_HOSTNAME

    url_app = Flask("test_blobstream_urls")
    url_app.config["SERVER_HOSTNAME"] = TEST_SERVER_HOSTNAME
    url_app.config["PREFERRED_URL_SCHEME"] = TEST_SCHEME
    return UpstreamProxy(url_app, real_instance_keys)


@pytest.fixture
def client(app):
    return app.test_client()


def _make_path(
    proxy,
    scheme=TEST_SCHEME,
    hostname=TEST_UPSTREAM_HOSTNAME,
    local_ns=TEST_LOCAL_NAMESPACE,
    upstream_ns=TEST_UPSTREAM_NAMESPACE,
    repo=TEST_UPSTREAM_REPO,
    digest=TEST_DIGEST,
):
    """
    Generates a valid /_upstream_proxy/... path using the given proxy
    instance.
    """
    created_url = proxy.create_upstream_proxy_url(
        scheme,
        hostname,
        local_ns,
        upstream_ns,
        repo,
        digest,
    )

    # trim scheme and prefix
    trimmed = created_url.split("/_upstream_proxy/")[1]
    full_url = "/_upstream_proxy/" + trimmed

    return full_url


class FakeUpstreamResponse:
    """
    Helper class that represents upstream responses.
    """

    def __init__(self, chunks, headers=None, status_code=200):
        self._chunks = chunks
        self.headers = headers or {}
        self.status_code = status_code
        self.closed = False

    def iter_content(self, chunk_size=None):
        """
        Yields content in chunks to the caller.
        """
        for chunk in self._chunks:
            yield chunk

    def close(self):
        self.closed = True


class TestBlobstreamFailures:
    @pytest.mark.parametrize(
        "path",
        [
            "/_upstream_proxy/token/https/host",
            f"/_upstream_proxy/token/https/host/wrongv2/ns/repo/blobs/{TEST_DIGEST}",
            f"/_upstream_proxy/token/https/host/v2/ns/repo/wrongblobs/{TEST_DIGEST}",
            "/_upstream_proxy/token/https/host/v2/ns/repo/blobs/md5:abc123",
            f"/_upstream_proxy/{BAD_TOKEN}/https/host/v2/ns/repo/blobs/{TEST_DIGEST}",
        ],
        ids=[
            "too_few_parts",
            "wrong_v2_segment",
            "wrong_blobs_segment",
            "non_sha256_digest",
            "invalid_base64_token",
        ],
    )
    def test_malformed_requests_return_401(self, client, path):
        """
        Ensures that a 401 is returned if a malformed path is detected
        in the proxy request.
        """
        resp = client.get(path)
        assert resp.status_code == 401

    @pytest.mark.parametrize(
        "tamper_fn",
        [
            lambda p: p.replace(f"/{TEST_SCHEME}/", "/http/", 1),
            lambda p: p.replace(TEST_UPSTREAM_HOSTNAME, "malicious.upstream.com"),
            lambda p: p.replace(f"/v2/{TEST_UPSTREAM_NAMESPACE}/", "/v2/evil_namespace/"),
            lambda p: p.replace(
                f"/v2/{TEST_UPSTREAM_NAMESPACE}/{TEST_UPSTREAM_REPO}",
                "/v2/{TEST_UPSTREAM_NAMESPACE}/troublesome_repo/",
            ),
            lambda p: p.replace(f"{TEST_DIGEST}", "sha256:bad-digest"),
        ],
        ids=[
            "scheme_mismatch",
            "hostname_mismatch",
            "namespace_mismatch",
            "repo_mismatch",
            "blob_sha_mismatch",
        ],
    )
    def test_tampered_access_fields_return_401(self, client, url_proxy, tamper_fn):
        """
        Verifies that tampered URLs are properly discarded and a 401
        is returned.
        """
        import logging

        path = _make_path(url_proxy)
        tampered = tamper_fn(path)
        logging.debug("Tampered token: %s", tampered)
        resp = client.get(tampered)
        assert resp.status_code == 401

    def test_proxy_cache_config_not_found_returns_401(self, client, url_proxy):
        """
        Verifies that requesting a blob via an organization that does not have
        a proxy config enabled returns a 401.
        """
        from data.model import InvalidProxyCacheConfigException

        path = _make_path(url_proxy)
        with patch(
            "endpoints.blobstream.get_proxy_cache_config_for_org",
            side_effect=InvalidProxyCacheConfigException,
        ):
            resp = client.get(path)

        assert resp.status_code == 401


class TestBlobstreamSuccess:
    def test_valid_request_streams_blob_and_returns_200(self, client, url_proxy):
        """
        Verifies that we can successfully stream content from an upstream
        location. Explicitly checks the returned content, it must match
        content that was served.
        """
        path = _make_path(url_proxy)
        fake_resp = FakeUpstreamResponse(
            [b"hello ", b"world"],
            headers={
                "content-length": "11",
                "content-type": "application/octet-stream",
            },
        )
        mock_proxy_instance = MagicMock()
        mock_proxy_instance.get_blob.return_value = fake_resp

        with (
            patch("endpoints.blobstream.get_proxy_cache_config_for_org", return_value=MagicMock()),
            patch("endpoints.blobstream.Proxy", return_value=mock_proxy_instance),
        ):
            resp = client.get(path)

        assert resp.status_code == 200
        assert resp.get_data() == b"hello world"
        assert resp.headers["Docker-Content-Digest"] == TEST_DIGEST
        assert resp.headers["Content-Length"] == "11"
        assert resp.headers["Content-Type"] == "application/octet-stream"
        assert fake_resp.closed is True

    def test_upstream_registry_error_returns_502(self, client, url_proxy):
        """
        Verifies that on upstream error we return a 502 to the client.
        """
        from proxy import UpstreamRegistryError

        path = _make_path(url_proxy)
        mock_proxy_instance = MagicMock()
        mock_proxy_instance.get_blob.side_effect = UpstreamRegistryError("boom")

        with (
            patch("endpoints.blobstream.get_proxy_cache_config_for_org", return_value=MagicMock()),
            patch("endpoints.blobstream.Proxy", return_value=mock_proxy_instance),
        ):
            resp = client.get(path)

        assert resp.status_code == 502

    @pytest.mark.parametrize("encoding", ["gzip", "GZIP", "deflate", "br", "zstd", "gzip, br"])
    def test_encoded_upstream_response_returns_502(self, client, url_proxy, encoding):
        """
        Verifies that an upstream which ignores Accept-Encoding: identity and
        applies a content encoding is rejected with a 502 instead of streaming
        decoded bytes under the encoded Content-Length/Content-Range. No body
        bytes may be sent and the upstream response must be closed.
        """
        path = _make_path(url_proxy)
        fake_resp = FakeUpstreamResponse(
            [b"should-never-be-sent"],
            headers={
                "content-length": "20",
                "content-encoding": encoding,
                "content-type": "application/octet-stream",
            },
        )
        mock_proxy_instance = MagicMock()
        mock_proxy_instance.get_blob.return_value = fake_resp

        with (
            patch("endpoints.blobstream.get_proxy_cache_config_for_org", return_value=MagicMock()),
            patch("endpoints.blobstream.Proxy", return_value=mock_proxy_instance),
        ):
            resp = client.get(path)

        assert resp.status_code == 502
        assert b"should-never-be-sent" not in resp.get_data()
        assert fake_resp.closed is True

    @pytest.mark.parametrize("headers_extra", [{}, {"content-encoding": "identity"}])
    def test_identity_or_missing_content_encoding_is_streamed(
        self, client, url_proxy, headers_extra
    ):
        """
        Verifies that a missing or explicit identity Content-Encoding does not
        trigger the rejection.
        """
        path = _make_path(url_proxy)
        fake_resp = FakeUpstreamResponse(
            [b"hello ", b"world"],
            headers={"content-length": "11", **headers_extra},
        )
        mock_proxy_instance = MagicMock()
        mock_proxy_instance.get_blob.return_value = fake_resp

        with (
            patch("endpoints.blobstream.get_proxy_cache_config_for_org", return_value=MagicMock()),
            patch("endpoints.blobstream.Proxy", return_value=mock_proxy_instance),
        ):
            resp = client.get(path)

        assert resp.status_code == 200
        assert resp.get_data() == b"hello world"

    def test_stream_failure_is_logged_and_reraised(self, client, url_proxy, caplog):
        """
        Verifies that the exception is re-raised and properly passed
        downstream to be logged.
        """
        path = _make_path(url_proxy)

        # return a chunk of data and then raise an exception
        def raising_chunks():
            yield b"partial-data"
            raise ConnectionError("upstream reset mid-flight")

        fake_resp = FakeUpstreamResponse(raising_chunks())
        mock_proxy_instance = MagicMock()
        mock_proxy_instance.get_blob.return_value = fake_resp

        with (
            patch("endpoints.blobstream.get_proxy_cache_config_for_org", return_value=MagicMock()),
            patch("endpoints.blobstream.Proxy", return_value=mock_proxy_instance),
        ):
            with pytest.raises(ConnectionError):
                resp = client.get(path)
                resp.get_data()

        assert fake_resp.closed is True
        assert "Upstream blob broke after" in caplog.text

    def test_stream_file_of_random_data_returns_200_with_proper_digest(self, client, url_proxy):
        """
        Similar to previously passing tests, only this time the test is on a
        20 MiB blob which is randomly generated. Verifies that the calculated
        digest before serving matches the SHA digest of the received data and
        verifies that the Docker-Content-Digest header and other headers are
        properly set.
        """
        import hashlib
        import os

        # create a relatively big file for serving
        # size here is not on byte boundaires, the last chunk will be
        # less than the max chunk size that the generator yields
        blob_data = os.urandom(21729503)
        digest = "sha256:" + hashlib.sha256(blob_data).hexdigest()

        path = _make_path(url_proxy, digest=digest)

        # split into chunks so that the multiyielder loop is actually
        # excersized
        chunk_size = 1024 * 1024
        chunks = [blob_data[i : i + chunk_size] for i in range(0, len(blob_data), chunk_size)]

        # construct a fake response
        fake_resp = FakeUpstreamResponse(
            chunks,
            headers={
                "content-length": str(len(blob_data)),
            },
        )

        mock_proxy_instance = MagicMock()
        mock_proxy_instance.get_blob.return_value = fake_resp

        with (
            patch("endpoints.blobstream.get_proxy_cache_config_for_org", return_value=MagicMock()),
            patch("endpoints.blobstream.Proxy", return_value=mock_proxy_instance),
        ):
            resp = client.get(path)

        assert resp.status_code == 200
        downloaded = resp.get_data()
        downloaded_digest = "sha256:" + hashlib.sha256(downloaded).hexdigest()

        assert downloaded_digest == digest
        assert resp.headers["Docker-Content-Digest"] == digest
        assert fake_resp.closed is True

    def test_range_header_is_forwarded_to_upstream(self, client, url_proxy):
        """
        Verifies that the range header is properly forwarded to upstream.
        """
        path = _make_path(url_proxy)
        fake_resp = FakeUpstreamResponse([b"partial"], status_code=206)
        mock_proxy_instance = MagicMock()
        mock_proxy_instance.get_blob.return_value = fake_resp

        with (
            patch("endpoints.blobstream.get_proxy_cache_config_for_org", return_value=MagicMock()),
            patch("endpoints.blobstream.Proxy", return_value=mock_proxy_instance),
        ):
            client.get(
                path,
                headers={
                    "Range": "bytes=100-199",
                },
            )

        mock_proxy_instance.get_blob.assert_called_once_with(
            TEST_DIGEST,
            additional_headers={
                "Range": "bytes=100-199",
            },
        )

    def test_partial_content_response_is_relayed(self, client, url_proxy):
        """
        Verifies that the proper headers and response code are relayed
        to the caller from upstream.
        """
        path = _make_path(url_proxy)
        fake_resp = FakeUpstreamResponse(
            [b"partial-bytes"],
            headers={
                "content-range": "bytes 100-199/1000",
                "accept-ranges": "bytes",
                "content-length": "100",
            },
            status_code=206,
        )

        mock_proxy_instance = MagicMock()
        mock_proxy_instance.get_blob.return_value = fake_resp

        with (
            patch("endpoints.blobstream.get_proxy_cache_config_for_org", return_value=MagicMock()),
            patch("endpoints.blobstream.Proxy", return_value=mock_proxy_instance),
        ):
            resp = client.get(
                path,
                headers={
                    "Range": "bytes=100-199",
                },
            )

        assert resp.status_code == 206
        assert resp.headers["Content-Range"] == "bytes 100-199/1000"
        assert resp.headers["Accept-Ranges"] == "bytes"
        assert resp.get_data() == b"partial-bytes"

    def test_range_requests_reassemble_to_original_blob(self, client, url_proxy):
        """
        Verifies that the reassembly of several chunks of a 1 MiB layer filled
        with random data is consistent and that the calculated SHA digest of
        received data is the same as the SHA digest of the original data.
        """
        import hashlib
        import os

        blob_data = os.urandom(1024 * 1024)
        digest = "sha256:" + hashlib.sha256(blob_data).hexdigest()
        total_len = len(blob_data)

        path = _make_path(url_proxy, digest=digest)

        def fake_get_blob(digest, additional_headers=None):
            """
            Helper function that mimicks proxy's get_blob. Returns
            chunks of data based on the requested range.
            """
            range_header = (additional_headers or {}).get("Range")
            _, _, range_spec = range_header.partition("=")

            start_str, _, end_str = range_spec.partition("-")
            start, end = int(start_str), int(end_str)

            # generate a chunk based on start and end positions
            sliced = blob_data[start : end + 1]

            return FakeUpstreamResponse(
                [sliced],
                headers={
                    "content-range": f"bytes {start}-{end}/{total_len}",
                    "content-length": str(len(sliced)),
                    "accept-ranges": "bytes",
                },
                status_code=206,
            )

        mock_proxy_instance = MagicMock()
        mock_proxy_instance.get_blob.side_effect = fake_get_blob

        # ranges are intentionally uneven (not on byte boundaries)
        chunk_ranges = [(0, 317772), (317773, 729773), (729774, total_len - 1)]

        downloaded = b""

        with (
            patch("endpoints.blobstream.get_proxy_cache_config_for_org", return_value=MagicMock()),
            patch("endpoints.blobstream.Proxy", return_value=mock_proxy_instance),
        ):
            for start, end in chunk_ranges:
                resp = client.get(
                    path,
                    headers={
                        "Range": f"bytes={start}-{end}",
                    },
                )
                assert resp.status_code == 206
                assert resp.headers["Content-Range"] == f"bytes {start}-{end}/{total_len}"
                downloaded += resp.get_data()

        assert len(downloaded) == total_len
        assert "sha256:" + hashlib.sha256(downloaded).hexdigest() == digest


class TestBlobStreamFeatureFlag:
    def test_feature_disabled_returns_404(self):
        """
        Verifies that we get a proper 404 back on the _upstream_proxy
        endpoint if features.PROXY_CACHE is disabled. To do this, we
        need to re-instantiate the app from scratch after configuration
        change, run the test, and then restore the original setup
        so other tests can run properly.
        """
        import endpoints.blobstream as blobstream_module

        try:
            with toggle_feature("PROXY_CACHE", False):
                importlib.reload(blobstream_module)

                isolated_app = Flask("test_blobstream_feature_disabled")
                isolated_app.register_blueprint(
                    blobstream_module.blobstream_bp, url_prefix="/_upstream_proxy"
                )

                resp = isolated_app.test_client().get("/_upstream_proxy/anything/at/all")
                assert resp.status_code == 404

        finally:
            importlib.reload(blobstream_module)
