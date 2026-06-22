import base64
import importlib
import json
import os
import uuid
from unittest.mock import patch

import pytest
from httmock import HTTMock, urlmatch

from util.bootstrap_token import (
    DEFAULT_BOOTSTRAP_TOKEN_PATH,
    KubernetesTokenProvider,
    read_bootstrap_token,
    read_token_file,
    write_bootstrap_token,
    write_token_file,
)

# ---------------------------------------------------------------------------
# write_token_file tests (Phase 1)
# ---------------------------------------------------------------------------


def test_write_token_file_creates_file(tmp_path):
    path = str(tmp_path / "token.json")
    write_token_file(path, "mytoken123")

    with open(path) as f:
        data = json.load(f)
    assert data == {"access_token": "mytoken123"}


def test_write_token_file_permissions(tmp_path):
    path = str(tmp_path / "token.json")
    write_token_file(path, "tok")

    mode = os.stat(path).st_mode & 0o777
    assert mode == 0o600


def test_write_token_file_creates_parents(tmp_path):
    path = str(tmp_path / "a" / "b" / "token.json")
    write_token_file(path, "tok")
    assert os.path.exists(path)


def test_write_token_file_overwrites_existing(tmp_path):
    path = str(tmp_path / "token.json")
    write_token_file(path, "old")
    write_token_file(path, "new")

    with open(path) as f:
        assert json.load(f)["access_token"] == "new"


def test_write_token_file_invalid_path_raises():
    with pytest.raises(OSError):
        write_token_file("/proc/nonexistent/path/token.json", "tok")


def test_read_token_file(tmp_path):
    path = str(tmp_path / "token.json")
    write_token_file(path, "mytoken123")

    assert read_token_file(path) == "mytoken123"


def test_read_token_file_missing_or_malformed(tmp_path):
    path = tmp_path / "token.json"
    assert read_token_file(str(path)) is None

    path.write_text("not-json")
    assert read_token_file(str(path)) is None


# ---------------------------------------------------------------------------
# KubernetesTokenProvider tests
# ---------------------------------------------------------------------------


def _setup_sa_files(tmp_path, namespace="test-ns"):
    sa_token_path = str(tmp_path / "sa-token")
    sa_ns_path = str(tmp_path / "sa-namespace")
    sa_ca_path = str(tmp_path / "ca.crt")
    token_value = str(uuid.uuid4())

    with open(sa_token_path, "w") as f:
        f.write(token_value)
    with open(sa_ns_path, "w") as f:
        f.write(namespace)
    with open(sa_ca_path, "w") as f:
        f.write("dummy-ca-cert")

    return sa_token_path, sa_ns_path, sa_ca_path, token_value


def test_k8s_provider_writes_secret(tmp_path):
    sa_token_path, sa_ns_path, sa_ca_path, auth_token = _setup_sa_files(tmp_path)
    hostname = "k8s-test-api"
    secret_name = "bootstrap-token"
    key_name = "token.json"

    existing_secret = {
        "kind": "Secret",
        "apiVersion": "v1",
        "metadata": {"name": secret_name},
        "data": {},
    }
    put_body = {}

    @urlmatch(netloc=hostname, path=r".*/secrets/bootstrap-token$", method="get")
    def get_secret(_, __):
        return {"status_code": 200, "content": json.dumps(existing_secret)}

    @urlmatch(netloc=hostname, path=r".*/secrets/bootstrap-token$", method="put")
    def put_secret(_, request):
        put_body.update(json.loads(request.body))
        return {"status_code": 200, "content": json.dumps(put_body)}

    @urlmatch(netloc=hostname)
    def catch_all(url, _):
        return {"status_code": 404, "content": "{}"}

    with HTTMock(get_secret, put_secret, catch_all):
        with patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path):
            with patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path):
                provider = KubernetesTokenProvider(
                    secret_name, key_name, api_host=hostname, sa_token_path=sa_token_path
                )
                provider.write_token("test-access-token")

    assert key_name in put_body["data"]
    decoded = base64.b64decode(put_body["data"][key_name]).decode("utf-8")
    assert json.loads(decoded) == {"access_token": "test-access-token"}


def test_k8s_provider_reads_secret(tmp_path):
    sa_token_path, sa_ns_path, sa_ca_path, _ = _setup_sa_files(tmp_path)
    hostname = "k8s-test-api"
    token_json = json.dumps({"access_token": "test-access-token"})
    existing_secret = {
        "kind": "Secret",
        "apiVersion": "v1",
        "data": {"token.json": base64.b64encode(token_json.encode("utf-8")).decode("ascii")},
    }

    @urlmatch(netloc=hostname, path=r".*/secrets/bootstrap-token$", method="get")
    def get_secret(_, __):
        return {"status_code": 200, "content": json.dumps(existing_secret)}

    @urlmatch(netloc=hostname)
    def catch_all(url, _):
        return {"status_code": 404, "content": "{}"}

    with HTTMock(get_secret, catch_all):
        with patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path):
            with patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path):
                provider = KubernetesTokenProvider(
                    "bootstrap-token", "token.json", api_host=hostname, sa_token_path=sa_token_path
                )
                assert provider.read_token() == "test-access-token"


def test_k8s_provider_secret_not_found(tmp_path):
    sa_token_path, sa_ns_path, sa_ca_path, _ = _setup_sa_files(tmp_path)
    hostname = "k8s-test-api"

    @urlmatch(netloc=hostname, path=r".*/secrets/.*", method="get")
    def get_secret(_, __):
        return {"status_code": 404, "content": "{}"}

    @urlmatch(netloc=hostname)
    def catch_all(url, _):
        return {"status_code": 404, "content": "{}"}

    with HTTMock(get_secret, catch_all):
        with patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path):
            with patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path):
                provider = KubernetesTokenProvider(
                    "missing-secret", "token.json", api_host=hostname, sa_token_path=sa_token_path
                )
                with pytest.raises(OSError, match="not found"):
                    provider.write_token("tok")


def test_k8s_provider_api_failure(tmp_path):
    sa_token_path, sa_ns_path, sa_ca_path, _ = _setup_sa_files(tmp_path)
    hostname = "k8s-test-api"

    existing_secret = {"kind": "Secret", "apiVersion": "v1", "data": {}}

    @urlmatch(netloc=hostname, path=r".*/secrets/.*", method="get")
    def get_secret(_, __):
        return {"status_code": 200, "content": json.dumps(existing_secret)}

    @urlmatch(netloc=hostname, path=r".*/secrets/.*", method="put")
    def put_secret(_, __):
        return {"status_code": 500, "content": "internal server error"}

    @urlmatch(netloc=hostname)
    def catch_all(url, _):
        return {"status_code": 404, "content": "{}"}

    with HTTMock(get_secret, put_secret, catch_all):
        with patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path):
            with patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path):
                provider = KubernetesTokenProvider(
                    "my-secret", "token.json", api_host=hostname, sa_token_path=sa_token_path
                )
                with pytest.raises(OSError, match="Failed to update"):
                    provider.write_token("tok")


def test_k8s_provider_missing_ca_cert(tmp_path):
    sa_token_path, sa_ns_path, _, _ = _setup_sa_files(tmp_path)

    with patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path):
        with patch.object(
            KubernetesTokenProvider, "SA_CA_CERT_PATH", str(tmp_path / "nonexistent-ca.crt")
        ):
            with pytest.raises(OSError, match="CA certificate"):
                KubernetesTokenProvider(
                    "my-secret", "token.json", api_host="k8s-api", sa_token_path=sa_token_path
                )


# ---------------------------------------------------------------------------
# write_bootstrap_token tests
# ---------------------------------------------------------------------------


def test_default_bootstrap_token_path_matches_config():
    from config import DefaultConfig

    assert DEFAULT_BOOTSTRAP_TOKEN_PATH == "/var/lib/quay/quay-machine-token.json"
    assert DefaultConfig.PROGRAMMATIC_TOKEN_PATH == DEFAULT_BOOTSTRAP_TOKEN_PATH


def test_write_bootstrap_token_file_only(tmp_path):
    config = {
        "PROGRAMMATIC_TOKEN_PATH": str(tmp_path / "token.json"),
    }
    with patch("util.bootstrap_token.IS_KUBERNETES", False):
        write_bootstrap_token(config, "mytoken")

    with open(str(tmp_path / "token.json")) as f:
        assert json.load(f)["access_token"] == "mytoken"


def test_read_bootstrap_token_file_only(tmp_path):
    config = {
        "PROGRAMMATIC_TOKEN_PATH": str(tmp_path / "token.json"),
    }
    write_token_file(config["PROGRAMMATIC_TOKEN_PATH"], "mytoken")

    with patch("util.bootstrap_token.IS_KUBERNETES", False):
        assert read_bootstrap_token(config) == "mytoken"


def test_write_bootstrap_token_k8s_does_not_write_local_file(tmp_path):
    sa_token_path, sa_ns_path, sa_ca_path, _ = _setup_sa_files(tmp_path)
    hostname = "k8s-test-api"
    token_path = str(tmp_path / "token.json")
    secret_name = "bootstrap-token"

    existing_secret = {"kind": "Secret", "apiVersion": "v1", "data": {}}
    put_body = {}

    @urlmatch(netloc=hostname, path=r".*/secrets/bootstrap-token$", method="get")
    def get_secret(_, __):
        return {"status_code": 200, "content": json.dumps(existing_secret)}

    @urlmatch(netloc=hostname, path=r".*/secrets/bootstrap-token$", method="put")
    def put_secret(_, request):
        put_body.update(json.loads(request.body))
        return {"status_code": 200, "content": json.dumps(put_body)}

    @urlmatch(netloc=hostname)
    def catch_all(url, _):
        return {"status_code": 404, "content": "{}"}

    config = {
        "PROGRAMMATIC_TOKEN_PATH": token_path,
        "PROGRAMMATIC_TOKEN_K8S_SECRET": secret_name,
        "PROGRAMMATIC_TOKEN_K8S_KEY": "token.json",
        "PROGRAMMATIC_TOKEN_K8S_NAMESPACE": "test-ns",
    }
    with (
        patch("util.bootstrap_token.IS_KUBERNETES", True),
        patch("util.bootstrap_token.KUBERNETES_API_HOST", hostname),
        patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path),
        patch.object(KubernetesTokenProvider, "SA_TOKEN_PATH", sa_token_path),
        patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path),
        HTTMock(get_secret, put_secret, catch_all),
    ):
        write_bootstrap_token(config, "mytoken")

    assert "token.json" in put_body["data"]
    decoded = base64.b64decode(put_body["data"]["token.json"]).decode("utf-8")
    assert json.loads(decoded) == {"access_token": "mytoken"}
    assert not os.path.exists(token_path)


def test_write_bootstrap_token_k8s_fails_raises_oserror(tmp_path):
    sa_token_path, sa_ns_path, sa_ca_path, _ = _setup_sa_files(tmp_path)
    hostname = "k8s-test-api"

    existing_secret = {"kind": "Secret", "apiVersion": "v1", "data": {}}

    @urlmatch(netloc=hostname, path=r".*/secrets/.*", method="get")
    def get_secret(_, __):
        return {"status_code": 200, "content": json.dumps(existing_secret)}

    @urlmatch(netloc=hostname, path=r".*/secrets/.*", method="put")
    def put_secret(_, __):
        return {"status_code": 500, "content": "internal server error"}

    @urlmatch(netloc=hostname)
    def catch_all(url, _):
        return {"status_code": 404, "content": "{}"}

    config = {
        "PROGRAMMATIC_TOKEN_K8S_SECRET": "my-secret",
        "PROGRAMMATIC_TOKEN_K8S_KEY": "token.json",
        "PROGRAMMATIC_TOKEN_K8S_NAMESPACE": "test-ns",
    }
    with (
        patch("util.bootstrap_token.IS_KUBERNETES", True),
        patch("util.bootstrap_token.KUBERNETES_API_HOST", hostname),
        patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path),
        patch.object(KubernetesTokenProvider, "SA_TOKEN_PATH", sa_token_path),
        patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path),
        HTTMock(get_secret, put_secret, catch_all),
    ):
        with pytest.raises(OSError, match="Failed to update"):
            write_bootstrap_token(config, "new-token")


def test_write_bootstrap_token_no_secret_configured(tmp_path):
    config = {
        "PROGRAMMATIC_TOKEN_PATH": str(tmp_path / "token.json"),
        "PROGRAMMATIC_TOKEN_K8S_SECRET": None,
    }
    with patch("util.bootstrap_token.IS_KUBERNETES", True):
        write_bootstrap_token(config, "mytoken")

    with open(str(tmp_path / "token.json")) as f:
        assert json.load(f)["access_token"] == "mytoken"


def test_write_token_file_removes_temp_file_on_write_failure(tmp_path):
    path = str(tmp_path / "token.json")

    with patch("util.bootstrap_token.os.write", side_effect=OSError("boom")):
        with pytest.raises(OSError, match="boom"):
            write_token_file(path, "tok")

    assert not os.path.exists(path)
    assert list(tmp_path.glob("*.tmp")) == []


def test_k8s_provider_missing_service_account_token(tmp_path):
    _, _, sa_ca_path, _ = _setup_sa_files(tmp_path)

    with patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path):
        with pytest.raises(OSError, match="service account token"):
            KubernetesTokenProvider(
                "my-secret",
                "token.json",
                api_host="k8s-api",
                sa_token_path=str(tmp_path / "missing-token"),
            )


def test_k8s_provider_read_secret_not_found(tmp_path):
    sa_token_path, sa_ns_path, sa_ca_path, _ = _setup_sa_files(tmp_path)
    hostname = "k8s-test-api"

    @urlmatch(netloc=hostname, path=r".*/secrets/.*", method="get")
    def get_secret(_, __):
        return {"status_code": 404, "content": "{}"}

    with HTTMock(get_secret):
        with (
            patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path),
            patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path),
        ):
            provider = KubernetesTokenProvider(
                "missing-secret", "token.json", api_host=hostname, sa_token_path=sa_token_path
            )
            assert provider.read_token() is None


def test_k8s_provider_read_secret_error_raises(tmp_path):
    sa_token_path, sa_ns_path, sa_ca_path, _ = _setup_sa_files(tmp_path)
    hostname = "k8s-test-api"

    @urlmatch(netloc=hostname, path=r".*/secrets/.*", method="get")
    def get_secret(_, __):
        return {"status_code": 500, "content": "{}"}

    with HTTMock(get_secret):
        with (
            patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path),
            patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path),
        ):
            provider = KubernetesTokenProvider(
                "my-secret", "token.json", api_host=hostname, sa_token_path=sa_token_path
            )
            with pytest.raises(OSError, match="Failed to read"):
                provider.read_token()


def test_k8s_provider_read_secret_missing_key(tmp_path):
    sa_token_path, sa_ns_path, sa_ca_path, _ = _setup_sa_files(tmp_path)
    hostname = "k8s-test-api"
    existing_secret = {"kind": "Secret", "apiVersion": "v1", "data": {}}

    @urlmatch(netloc=hostname, path=r".*/secrets/.*", method="get")
    def get_secret(_, __):
        return {"status_code": 200, "content": json.dumps(existing_secret)}

    with HTTMock(get_secret):
        with (
            patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path),
            patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path),
        ):
            provider = KubernetesTokenProvider(
                "my-secret", "token.json", api_host=hostname, sa_token_path=sa_token_path
            )
            assert provider.read_token() is None


def test_k8s_provider_read_secret_malformed_token_returns_none(tmp_path):
    sa_token_path, sa_ns_path, sa_ca_path, _ = _setup_sa_files(tmp_path)
    hostname = "k8s-test-api"
    existing_secret = {
        "kind": "Secret",
        "apiVersion": "v1",
        "data": {"token.json": base64.b64encode(b"\xff").decode("ascii")},
    }

    @urlmatch(netloc=hostname, path=r".*/secrets/.*", method="get")
    def get_secret(_, __):
        return {"status_code": 200, "content": json.dumps(existing_secret)}

    with HTTMock(get_secret):
        with (
            patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path),
            patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path),
        ):
            provider = KubernetesTokenProvider(
                "my-secret", "token.json", api_host=hostname, sa_token_path=sa_token_path
            )
            assert provider.read_token() is None


def test_k8s_provider_read_api_exception_wrapped(tmp_path):
    sa_token_path, sa_ns_path, sa_ca_path, _ = _setup_sa_files(tmp_path)

    with (
        patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path),
        patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path),
    ):
        provider = KubernetesTokenProvider(
            "my-secret", "token.json", api_host="k8s-api", sa_token_path=sa_token_path
        )
        with patch.object(provider, "_execute_k8s_api", side_effect=RuntimeError("boom")):
            with pytest.raises(OSError, match="K8s API call failed: boom"):
                provider.read_token()


def test_k8s_provider_write_api_exception_wrapped(tmp_path):
    sa_token_path, sa_ns_path, sa_ca_path, _ = _setup_sa_files(tmp_path)
    hostname = "k8s-test-api"

    @urlmatch(netloc=hostname, path=r".*/secrets/.*", method="get")
    def get_secret(_, __):
        return {"status_code": 200, "content": "not-json"}

    with HTTMock(get_secret):
        with (
            patch.object(KubernetesTokenProvider, "SA_NAMESPACE_PATH", sa_ns_path),
            patch.object(KubernetesTokenProvider, "SA_CA_CERT_PATH", sa_ca_path),
        ):
            provider = KubernetesTokenProvider(
                "my-secret", "token.json", api_host=hostname, sa_token_path=sa_token_path
            )
            with pytest.raises(OSError, match="K8s API call failed"):
                provider.write_token("tok")


def test_read_bootstrap_token_k8s_uses_secret_provider():
    config = {
        "PROGRAMMATIC_TOKEN_K8S_SECRET": "bootstrap-token",
        "PROGRAMMATIC_TOKEN_K8S_KEY": "custom-token.json",
        "PROGRAMMATIC_TOKEN_K8S_NAMESPACE": "custom-ns",
    }
    with (
        patch("util.bootstrap_token.IS_KUBERNETES", True),
        patch("util.bootstrap_token.KubernetesTokenProvider") as provider_cls,
    ):
        provider_cls.return_value.read_token.return_value = "k8s-token"
        assert read_bootstrap_token(config) == "k8s-token"

    provider_cls.assert_called_once_with(
        "bootstrap-token", "custom-token.json", namespace="custom-ns"
    )


def test_kubernetes_api_host_includes_service_port(monkeypatch):
    import util.bootstrap_token as bootstrap_token

    with monkeypatch.context() as m:
        m.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
        m.setenv("KUBERNETES_SERVICE_PORT", "443")
        reloaded = importlib.reload(bootstrap_token)
        assert reloaded.KUBERNETES_API_HOST == "10.0.0.1:443"

    importlib.reload(bootstrap_token)
