import base64
import json
import os
from unittest.mock import patch

import pytest
from httmock import HTTMock, urlmatch

from config import DefaultConfig
from util.bootstrap_token import (
    DEFAULT_BOOTSTRAP_TOKEN_PATH,
    DEFAULT_KUBERNETES_TOKEN_KEY,
    MAX_BOOTSTRAP_TOKEN_FILE_BYTES,
    KubernetesTokenProvider,
    delete_bootstrap_token,
    delete_token_file,
    read_bootstrap_token,
    read_token_file,
    write_bootstrap_token,
    write_token_file,
)


def test_default_bootstrap_token_path_matches_config():
    assert DEFAULT_BOOTSTRAP_TOKEN_PATH == DefaultConfig.BOOTSTRAP_TOKEN_PATH


def test_write_token_file_creates_file_with_restrictive_permissions(tmp_path):
    path = str(tmp_path / "token.json")

    write_token_file(path, "mytoken123")

    with open(path) as f:
        assert json.load(f) == {"access_token": "mytoken123"}
    assert os.stat(path).st_mode & 0o777 == 0o600


def test_write_token_file_creates_parents_and_overwrites_existing_file(tmp_path):
    path = str(tmp_path / "a" / "b" / "token.json")

    write_token_file(path, "old")
    write_token_file(path, "new")

    with open(path) as f:
        assert json.load(f) == {"access_token": "new"}
    assert os.stat(tmp_path / "a" / "b").st_mode & 0o777 == 0o700


def test_write_token_file_invalid_path_raises_oserror():
    with pytest.raises(OSError):
        write_token_file("/proc/nonexistent/path/token.json", "tok")


def test_write_token_file_removes_temp_file_on_write_failure(tmp_path):
    path = str(tmp_path / "token.json")

    with patch("util.bootstrap_token.os.write", side_effect=OSError("boom")):
        with pytest.raises(OSError, match="boom"):
            write_token_file(path, "tok")

    assert not os.path.exists(path)
    assert list(tmp_path.glob("*.tmp")) == []


def test_read_token_file_returns_token(tmp_path):
    path = str(tmp_path / "token.json")
    write_token_file(path, "mytoken123")

    assert read_token_file(path) == "mytoken123"


def test_delete_token_file_removes_existing_file(tmp_path):
    path = str(tmp_path / "token.json")
    write_token_file(path, "mytoken123")

    assert delete_token_file(path) is True
    assert not os.path.exists(path)


def test_delete_token_file_missing_file_returns_false(tmp_path):
    path = str(tmp_path / "token.json")

    assert delete_token_file(path) is False


@pytest.mark.parametrize(
    "content",
    [
        None,
        "not-json",
        "{}",
        json.dumps({"access_token": ""}),
        json.dumps({"access_token": None}),
        json.dumps({"access_token": 123}),
        json.dumps(["not", "object"]),
    ],
)
def test_read_token_file_missing_or_malformed_returns_none(tmp_path, content):
    path = tmp_path / "token.json"
    if content is not None:
        path.write_text(content)

    assert read_token_file(str(path)) is None


def test_read_token_file_invalid_utf8_returns_none(tmp_path):
    path = tmp_path / "token.json"
    path.write_bytes(b"\xff\xfe\x00")

    assert read_token_file(str(path)) is None


@pytest.mark.parametrize("error", [IsADirectoryError, PermissionError])
def test_read_token_file_open_os_error_returns_none(error):
    with patch("builtins.open", side_effect=error("boom")):
        assert read_token_file("/unreadable/token.json") is None


def test_read_token_file_oversized_returns_none(tmp_path):
    path = tmp_path / "token.json"
    path.write_text("{" + " " * MAX_BOOTSTRAP_TOKEN_FILE_BYTES + "}")

    assert read_token_file(str(path)) is None


def test_write_and_read_bootstrap_token_uses_configured_path(tmp_path):
    config = {"BOOTSTRAP_TOKEN_PATH": str(tmp_path / "token.json")}

    write_bootstrap_token(config, "mytoken")

    assert read_bootstrap_token(config) == "mytoken"


def test_delete_bootstrap_token_uses_configured_path(tmp_path):
    config = {"BOOTSTRAP_TOKEN_PATH": str(tmp_path / "token.json")}
    write_bootstrap_token(config, "mytoken")

    assert delete_bootstrap_token(config) is True
    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])


def test_delete_bootstrap_token_missing_file_returns_false(tmp_path):
    config = {"BOOTSTRAP_TOKEN_PATH": str(tmp_path / "token.json")}

    assert delete_bootstrap_token(config) is False


def test_programmatic_token_k8s_defaults_match_config():
    assert DefaultConfig.PROGRAMMATIC_TOKEN_K8S_SECRET is None
    assert DefaultConfig.PROGRAMMATIC_TOKEN_K8S_KEY == DEFAULT_KUBERNETES_TOKEN_KEY
    assert DefaultConfig.PROGRAMMATIC_TOKEN_K8S_NAMESPACE is None


@pytest.fixture
def k8s_service_account(tmp_path, monkeypatch):
    service_account_dir = tmp_path / "serviceaccount"
    service_account_dir.mkdir()
    token_path = service_account_dir / "token"
    namespace_path = service_account_dir / "namespace"
    ca_path = service_account_dir / "ca.crt"

    token_path.write_text("service-account-token\n")
    namespace_path.write_text("quay-enterprise\n")
    ca_path.write_text("ca")

    monkeypatch.setattr(KubernetesTokenProvider, "SA_TOKEN_PATH", str(token_path))
    monkeypatch.setattr(KubernetesTokenProvider, "SA_NAMESPACE_PATH", str(namespace_path))
    monkeypatch.setattr(KubernetesTokenProvider, "SA_CA_CERT_PATH", str(ca_path))
    monkeypatch.setattr("util.bootstrap_token.KUBERNETES_API_HOST", "kubernetes.default.svc:443")

    return {
        "token_path": token_path,
        "namespace_path": namespace_path,
        "ca_path": ca_path,
    }


def _k8s_config(tmp_path, **overrides):
    config = {
        "BOOTSTRAP_TOKEN_PATH": str(tmp_path / "local-token.json"),
        "PROGRAMMATIC_TOKEN_K8S_SECRET": "bootstrap-token",
        "PROGRAMMATIC_TOKEN_K8S_KEY": "token.json",
    }
    config.update(overrides)
    return config


def _encode_token_json(access_token):
    return base64.b64encode(json.dumps({"access_token": access_token}).encode("utf-8")).decode(
        "ascii"
    )


def _request_body_json(request):
    body = request.body.decode("utf-8") if isinstance(request.body, bytes) else request.body
    return json.loads(body)


def _k8s_secret_handlers(secret, get_status=200, put_status=200, namespace="quay-enterprise"):
    requests = []
    path = "/api/v1/namespaces/%s/secrets/bootstrap-token$" % namespace

    @urlmatch(netloc="kubernetes.default.svc:443", path=path, method="get")
    def get_secret(_, request):
        requests.append(("GET", request))
        return {"status_code": get_status, "content": json.dumps(secret)}

    @urlmatch(netloc="kubernetes.default.svc:443", path=path, method="put")
    def put_secret(_, request):
        requests.append(("PUT", request))
        secret.clear()
        secret.update(_request_body_json(request))
        return {"status_code": put_status, "content": json.dumps(secret)}

    return requests, get_secret, put_secret


def test_local_fallback_when_not_running_in_kubernetes(tmp_path, monkeypatch):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", False)
    config = _k8s_config(tmp_path)

    write_bootstrap_token(config, "local-token")

    assert read_bootstrap_token(config) == "local-token"


def test_local_fallback_when_no_kubernetes_secret_is_configured(
    tmp_path, monkeypatch, k8s_service_account
):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    config = _k8s_config(tmp_path, PROGRAMMATIC_TOKEN_K8S_SECRET=None)

    write_bootstrap_token(config, "local-token")

    assert read_bootstrap_token(config) == "local-token"


def test_kubernetes_read_success(tmp_path, monkeypatch, k8s_service_account):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    config = _k8s_config(tmp_path)
    secret = {"data": {"token.json": _encode_token_json("k8s-token")}}
    _, get_secret, put_secret = _k8s_secret_handlers(secret)

    with HTTMock(get_secret, put_secret):
        assert read_bootstrap_token(config) == "k8s-token"


def test_kubernetes_read_missing_secret_returns_none(tmp_path, monkeypatch, k8s_service_account):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    config = _k8s_config(tmp_path)
    _, get_secret, put_secret = _k8s_secret_handlers({}, get_status=404)

    with HTTMock(get_secret, put_secret):
        assert read_bootstrap_token(config) is None


def test_kubernetes_read_missing_key_returns_none(tmp_path, monkeypatch, k8s_service_account):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    config = _k8s_config(tmp_path)
    secret = {"data": {"other.json": _encode_token_json("k8s-token")}}
    _, get_secret, put_secret = _k8s_secret_handlers(secret)

    with HTTMock(get_secret, put_secret):
        assert read_bootstrap_token(config) is None


@pytest.mark.parametrize("content", ["not-json", json.dumps(["not", "object"])])
def test_kubernetes_read_malformed_api_response_raises_oserror(
    tmp_path, monkeypatch, k8s_service_account, content
):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    config = _k8s_config(tmp_path)

    @urlmatch(
        netloc="kubernetes.default.svc:443",
        path="/api/v1/namespaces/quay-enterprise/secrets/bootstrap-token$",
        method="get",
    )
    def get_secret(_, __):
        return {"status_code": 200, "content": content}

    with HTTMock(get_secret):
        with pytest.raises(OSError):
            read_bootstrap_token(config)


@pytest.mark.parametrize(
    "encoded_token",
    [
        "not-base64",
        base64.b64encode(b"not-json").decode("ascii"),
        base64.b64encode(json.dumps({"access_token": ""}).encode("utf-8")).decode("ascii"),
        base64.b64encode(json.dumps({"access_token": 123}).encode("utf-8")).decode("ascii"),
        base64.b64encode(b"\xff\xfe").decode("ascii"),
    ],
)
def test_kubernetes_read_malformed_token_data_returns_none(
    tmp_path, monkeypatch, k8s_service_account, encoded_token
):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    config = _k8s_config(tmp_path)
    secret = {"data": {"token.json": encoded_token}}
    _, get_secret, put_secret = _k8s_secret_handlers(secret)

    with HTTMock(get_secret, put_secret):
        assert read_bootstrap_token(config) is None


def test_kubernetes_write_success_updates_configured_secret_key(
    tmp_path, monkeypatch, k8s_service_account
):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    config = _k8s_config(tmp_path, PROGRAMMATIC_TOKEN_K8S_KEY="custom-token_json.1")
    secret = {"data": {"other.json": "dmFsdWU="}}
    requests, get_secret, put_secret = _k8s_secret_handlers(secret)

    with HTTMock(get_secret, put_secret):
        write_bootstrap_token(config, "new-token")

    assert len(requests) == 2
    assert requests[0][1].headers["Accept"] == "application/json"
    assert requests[0][1].headers["Authorization"] == "Bearer service-account-token"
    assert requests[1][1].headers["Content-Type"] == "application/json"
    decoded = base64.b64decode(secret["data"]["custom-token_json.1"]).decode("utf-8")
    assert json.loads(decoded) == {"access_token": "new-token"}
    assert secret["data"]["other.json"] == "dmFsdWU="


def test_kubernetes_write_missing_secret_raises_oserror(tmp_path, monkeypatch, k8s_service_account):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    config = _k8s_config(tmp_path)
    _, get_secret, put_secret = _k8s_secret_handlers({}, get_status=404)

    with HTTMock(get_secret, put_secret):
        with pytest.raises(OSError):
            write_bootstrap_token(config, "new-token")


def test_kubernetes_write_get_failure_raises_oserror(tmp_path, monkeypatch, k8s_service_account):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    config = _k8s_config(tmp_path)
    _, get_secret, put_secret = _k8s_secret_handlers({}, get_status=500)

    with HTTMock(get_secret, put_secret):
        with pytest.raises(OSError):
            write_bootstrap_token(config, "new-token")


def test_kubernetes_write_put_failure_raises_oserror(tmp_path, monkeypatch, k8s_service_account):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    config = _k8s_config(tmp_path)
    secret = {"data": {}}
    _, get_secret, put_secret = _k8s_secret_handlers(secret, put_status=500)

    with HTTMock(get_secret, put_secret):
        with pytest.raises(OSError):
            write_bootstrap_token(config, "new-token")


def test_kubernetes_missing_service_account_token_fails_clearly(
    tmp_path, monkeypatch, k8s_service_account
):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    monkeypatch.setattr(KubernetesTokenProvider, "SA_TOKEN_PATH", str(tmp_path / "missing-token"))
    config = _k8s_config(tmp_path)

    with pytest.raises(OSError, match="service account token"):
        read_bootstrap_token(config)


def test_kubernetes_missing_service_account_ca_certificate_fails_clearly(
    tmp_path, monkeypatch, k8s_service_account
):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    monkeypatch.setattr(
        KubernetesTokenProvider, "SA_CA_CERT_PATH", str(tmp_path / "missing-ca.crt")
    )
    config = _k8s_config(tmp_path)

    with pytest.raises(OSError, match="CA certificate"):
        read_bootstrap_token(config)


def test_kubernetes_configured_namespace_overrides_service_account_namespace(
    tmp_path, monkeypatch, k8s_service_account
):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    k8s_service_account["namespace_path"].write_text("wrong-namespace\n")
    config = _k8s_config(tmp_path, PROGRAMMATIC_TOKEN_K8S_NAMESPACE="configured-namespace")
    secret = {"data": {"token.json": _encode_token_json("k8s-token")}}
    _, get_secret, put_secret = _k8s_secret_handlers(secret, namespace="configured-namespace")

    with HTTMock(get_secret, put_secret):
        assert read_bootstrap_token(config) == "k8s-token"


def test_kubernetes_default_namespace_is_read_from_service_account_namespace_file(
    tmp_path, monkeypatch, k8s_service_account
):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    k8s_service_account["namespace_path"].write_text("service-account-namespace\n")
    config = _k8s_config(tmp_path)
    secret = {"data": {"token.json": _encode_token_json("k8s-token")}}
    _, get_secret, put_secret = _k8s_secret_handlers(secret, namespace="service-account-namespace")

    with HTTMock(get_secret, put_secret):
        assert read_bootstrap_token(config) == "k8s-token"


def test_kubernetes_delete_removes_configured_secret_key(
    tmp_path, monkeypatch, k8s_service_account
):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    config = _k8s_config(tmp_path)
    secret = {"data": {"token.json": _encode_token_json("k8s-token"), "other.json": "dmFsdWU="}}
    _, get_secret, put_secret = _k8s_secret_handlers(secret)

    with HTTMock(get_secret, put_secret):
        assert delete_bootstrap_token(config) is True

    assert "token.json" not in secret["data"]
    assert secret["data"]["other.json"] == "dmFsdWU="


def test_kubernetes_delete_missing_secret_returns_false(tmp_path, monkeypatch, k8s_service_account):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    config = _k8s_config(tmp_path)
    _, get_secret, put_secret = _k8s_secret_handlers({}, get_status=404)

    with HTTMock(get_secret, put_secret):
        assert delete_bootstrap_token(config) is False


def test_kubernetes_delete_missing_key_returns_false(tmp_path, monkeypatch, k8s_service_account):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    config = _k8s_config(tmp_path)
    secret = {"data": {"other.json": "dmFsdWU="}}
    _, get_secret, put_secret = _k8s_secret_handlers(secret)

    with HTTMock(get_secret, put_secret):
        assert delete_bootstrap_token(config) is False


def test_kubernetes_delete_update_failure_raises_oserror(
    tmp_path, monkeypatch, k8s_service_account
):
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    config = _k8s_config(tmp_path)
    secret = {"data": {"token.json": _encode_token_json("k8s-token")}}
    _, get_secret, put_secret = _k8s_secret_handlers(secret, put_status=500)

    with HTTMock(get_secret, put_secret):
        with pytest.raises(OSError):
            delete_bootstrap_token(config)
