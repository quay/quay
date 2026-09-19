import base64
import json
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from httmock import HTTMock, urlmatch

from app import app as real_app
from auth.kubernetes_sa import (
    KubernetesSATokenValidationError,
    KubernetesSATokenValidator,
    ValidatedKubernetesSA,
)
from data import model
from endpoints.api.bootstrap import (
    _QUAY_BOOTSTRAP_RENEWAL_LOCATION_HEADER,
    BootstrapExchangeError,
    _exchange_bootstrap_token,
)
from endpoints.test.shared import client_with_identity
from test.fixtures import *
from util.bootstrap_token import KubernetesTokenProvider


def _bootstrap_config(tmp_path, owner="devtable"):
    return {
        "FEATURE_PROGRAMMATIC_BOOTSTRAP": True,
        "SUPER_USERS": [owner],
        "BOOTSTRAP_TOKEN_OWNER": owner,
        "BOOTSTRAP_TOKEN_PATH": str(tmp_path / "token.json"),
        "BOOTSTRAP_TOKEN_EXPIRATION": 3600,
        "BOOTSTRAP_TOKEN_SCOPE": "repo:read",
    }


def _k8s_bootstrap_config(tmp_path, owner="devtable"):
    config = _bootstrap_config(tmp_path, owner=owner)
    config.update(
        {
            "PROGRAMMATIC_TOKEN_K8S_SECRET": "bootstrap-token",
            "PROGRAMMATIC_TOKEN_K8S_KEY": "token.json",
        }
    )
    return config


def _exchange_endpoint_config(tmp_path, owner="devtable"):
    issuer = "https://kubernetes.default.svc"
    subject = "system:serviceaccount:quay-operator:controller-manager"
    config = _bootstrap_config(tmp_path, owner=owner)
    config.update(
        {
            "FEATURE_KUBERNETES_SA_BOOTSTRAP": True,
            "KUBERNETES_SA_BOOTSTRAP_CONFIG": {
                "ISSUERS": [{"ISSUER": issuer}],
                "AUTHORIZED_SUBJECTS": [
                    {
                        "ISSUER": issuer,
                        "SUBJECT": subject,
                        "SCOPES": "repo:read repo:write",
                    }
                ],
                "BOOTSTRAP_TOKEN_MAX_TTL": 600,
            },
        }
    )
    return config, ValidatedKubernetesSA(
        issuer, subject, {"exp": datetime.now(UTC).timestamp() + 3600}
    )


def _create_bootstrap_token(config):
    owner = model.user.get_user(config["BOOTSTRAP_TOKEN_OWNER"])
    application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        owner,
    )
    token_record, access_token = model.oauth.create_bootstrap_oauth_api_token(
        application,
        owner,
        "repo:read repo:write",
    )
    return owner, application, token_record, access_token


def _stored_access_token(config):
    with open(config["BOOTSTRAP_TOKEN_PATH"]) as f:
        return json.load(f)["access_token"]


def _patch_k8s_service_account(tmp_path, monkeypatch):
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
    monkeypatch.setattr("util.bootstrap_token.IS_KUBERNETES", True)
    monkeypatch.setattr("util.bootstrap_token.KUBERNETES_API_HOST", "kubernetes.default.svc:443")


def _k8s_secret_handlers(secret):
    @urlmatch(
        netloc="kubernetes.default.svc:443",
        path="/api/v1/namespaces/quay-enterprise/secrets/bootstrap-token$",
        method="get",
    )
    def get_secret(_, __):
        return {"status_code": 200, "content": json.dumps(secret)}

    @urlmatch(
        netloc="kubernetes.default.svc:443",
        path="/api/v1/namespaces/quay-enterprise/secrets/bootstrap-token$",
        method="put",
    )
    def put_secret(_, request):
        body = request.body.decode("utf-8") if isinstance(request.body, bytes) else request.body
        secret.clear()
        secret.update(json.loads(body))
        return {"status_code": 200, "content": json.dumps(secret)}

    return get_secret, put_secret


def _k8s_secret_access_token(secret, key="token.json"):
    token_json = base64.b64decode(secret["data"][key]).decode("utf-8")
    return json.loads(token_json)["access_token"]


def _expired_time():
    return datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)


def test_exchange_uses_shared_validator_cache_and_mints_bounded_token(
    app, initialized_db, tmp_path
):
    config, validated = _exchange_endpoint_config(tmp_path)
    form = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": "service-account-jwt",
        "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
        "scope": "repo:read",
    }

    with (
        patch.dict(real_app.config, config),
        patch.object(KubernetesSATokenValidator, "validate", return_value=validated) as validate,
        app.test_request_context(method="POST", data=form),
    ):
        payload, status, headers = _exchange_bootstrap_token()

    assert status == 200
    assert payload["scope"] == "repo:read"
    assert payload["expires_in"] == 600
    assert headers["Cache-Control"] == "no-store"
    validate.assert_called_once_with("service-account-jwt")


def test_exchange_audit_success_contains_safe_correlation_metadata(app, initialized_db, tmp_path):
    config, validated = _exchange_endpoint_config(tmp_path)
    form = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": "service-account-jwt",
        "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
        "scope": "repo:write repo:read repo:read",
    }

    with (
        patch.dict(real_app.config, config),
        patch.object(KubernetesSATokenValidator, "validate", return_value=validated),
        patch("endpoints.api.bootstrap.log_action") as audit,
        app.test_request_context(method="POST", data=form),
    ):
        payload, _, _ = _exchange_bootstrap_token()

    kind, account_name = audit.call_args.args[:2]
    metadata = audit.call_args.kwargs["metadata"]
    token_record = model.oauth.validate_access_token(payload["access_token"])
    application = token_record.application
    assert kind == "workload_identity_token_exchange"
    assert account_name == "devtable"
    assert metadata == {
        "outcome": "success",
        "requested_scope": "repo:read repo:write",
        "effective_scope": "repo:read repo:write",
        "issuer": validated.issuer,
        "subject": validated.subject,
        "oauth_token_uuid": token_record.uuid,
        "client_id": application.client_id,
    }
    assert "service-account-jwt" not in repr(metadata)
    assert all(secret_key not in metadata for secret_key in ("subject_token", "jti", "kid"))


def test_exchange_invalid_request_uses_matching_api_error_type(app, initialized_db, tmp_path):
    config, _ = _exchange_endpoint_config(tmp_path)

    with (
        patch.dict(real_app.config, config),
        patch("endpoints.api.bootstrap.log_action") as audit,
        app.test_request_context(method="POST", data={}),
        pytest.raises(BootstrapExchangeError) as exc_info,
    ):
        _exchange_bootstrap_token()

    assert exc_info.value.code == 400
    assert exc_info.value.data["error"] == "invalid_request"
    assert exc_info.value.data["error_type"] == "invalid_request"
    assert exc_info.value.data["title"] == "invalid_request"
    kind, account_name = audit.call_args.args[:2]
    metadata = audit.call_args.kwargs["metadata"]
    assert kind == "workload_identity_token_exchange_failed"
    assert account_name == "devtable"
    assert metadata == {
        "outcome": "failure",
        "requested_scope": "",
        "failure_category": "request",
        "failure_reason": "invalid_request",
    }


def test_exchange_access_denied_uses_unauthorized_api_error_type(app, initialized_db, tmp_path):
    config, validated = _exchange_endpoint_config(tmp_path)
    denied = ValidatedKubernetesSA(
        validated.issuer,
        "system:serviceaccount:untrusted:workload",
        {},
    )
    form = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": "service-account-jwt",
        "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
    }

    with (
        patch.dict(real_app.config, config),
        patch.object(KubernetesSATokenValidator, "validate", return_value=denied),
        patch("endpoints.api.bootstrap.log_action") as audit,
        app.test_request_context(method="POST", data=form),
        pytest.raises(BootstrapExchangeError) as exc_info,
    ):
        _exchange_bootstrap_token()

    assert exc_info.value.code == 403
    assert exc_info.value.data["error"] == "access_denied"
    assert exc_info.value.data["error_type"] == "unauthorized"
    assert exc_info.value.data["title"] == "unauthorized"
    kind, account_name = audit.call_args.args[:2]
    metadata = audit.call_args.kwargs["metadata"]
    assert kind == "workload_identity_token_exchange_failed"
    assert account_name == "devtable"
    assert metadata["failure_category"] == "authorization"
    assert metadata["failure_reason"] == "subject_not_authorized"
    assert metadata["issuer"] == denied.issuer
    assert metadata["subject"] == denied.subject
    assert "service-account-jwt" not in repr(metadata)


def test_exchange_server_error_uses_matching_api_error_type(app, initialized_db, tmp_path):
    config, validated = _exchange_endpoint_config(tmp_path, owner="missing-owner")
    form = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": "service-account-jwt",
        "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
    }

    with (
        patch.dict(real_app.config, config),
        patch.object(KubernetesSATokenValidator, "validate", return_value=validated),
        patch("endpoints.api.bootstrap.log_action") as audit,
        app.test_request_context(method="POST", data=form),
        pytest.raises(BootstrapExchangeError) as exc_info,
    ):
        _exchange_bootstrap_token()

    assert exc_info.value.code == 500
    assert exc_info.value.data["error"] == "server_error"
    assert exc_info.value.data["error_type"] == "server_error"
    assert exc_info.value.data["title"] == "server_error"
    kind, account_name = audit.call_args.args[:2]
    metadata = audit.call_args.kwargs["metadata"]
    assert kind == "workload_identity_token_exchange_failed"
    assert account_name is None
    assert metadata["failure_category"] == "issuance"
    assert metadata["failure_reason"] == "token_owner_missing"
    assert metadata["issuer"] == validated.issuer
    assert metadata["subject"] == validated.subject


@pytest.mark.parametrize(
    ("category", "failure_category", "failure_reason"),
    [
        ("trust", "trust", "token_validation_failed"),
        ("identity", "identity", "service_account_identity_invalid"),
    ],
)
def test_exchange_validation_failures_use_stable_audit_taxonomy(
    app, initialized_db, tmp_path, category, failure_category, failure_reason
):
    config, _ = _exchange_endpoint_config(tmp_path)
    form = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": "service-account-jwt",
        "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
    }

    with (
        patch.dict(real_app.config, config),
        patch.object(
            KubernetesSATokenValidator,
            "validate",
            side_effect=KubernetesSATokenValidationError("presented jwt", category=category),
        ),
        patch("endpoints.api.bootstrap.log_action") as audit,
        app.test_request_context(method="POST", data=form),
        pytest.raises(BootstrapExchangeError),
    ):
        _exchange_bootstrap_token()

    metadata = audit.call_args.kwargs["metadata"]
    assert metadata["failure_category"] == failure_category
    assert metadata["failure_reason"] == failure_reason
    assert "presented jwt" not in repr(metadata)
    assert "service-account-jwt" not in repr(metadata)


def test_exchange_scope_denial_has_distinct_audit_reason(app, initialized_db, tmp_path):
    config, validated = _exchange_endpoint_config(tmp_path)
    form = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": "service-account-jwt",
        "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
        "scope": "repo:delete repo:read repo:read",
    }

    with (
        patch.dict(real_app.config, config),
        patch.object(KubernetesSATokenValidator, "validate", return_value=validated),
        patch("endpoints.api.bootstrap.log_action") as audit,
        app.test_request_context(method="POST", data=form),
        pytest.raises(BootstrapExchangeError),
    ):
        _exchange_bootstrap_token()

    metadata = audit.call_args.kwargs["metadata"]
    assert metadata["failure_category"] == "authorization"
    assert metadata["failure_reason"] == "scope_not_authorized"
    assert metadata["requested_scope"] == "repo:delete repo:read"
    assert metadata["issuer"] == validated.issuer
    assert metadata["subject"] == validated.subject


def test_exchange_application_creation_failure_is_audited_and_reraised(
    app, initialized_db, tmp_path
):
    config, validated = _exchange_endpoint_config(tmp_path)
    form = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": "service-account-jwt",
        "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
    }

    with (
        patch.dict(real_app.config, config),
        patch.object(KubernetesSATokenValidator, "validate", return_value=validated),
        patch.object(
            model.oauth,
            "get_canonical_bootstrap_application",
            side_effect=RuntimeError("application-secret"),
        ),
        patch("endpoints.api.bootstrap.log_action") as audit,
        app.test_request_context(method="POST", data=form),
        pytest.raises(RuntimeError, match="application-secret"),
    ):
        _exchange_bootstrap_token()

    metadata = audit.call_args.kwargs["metadata"]
    assert metadata["failure_category"] == "issuance"
    assert metadata["failure_reason"] == "application_creation_failed"
    assert "application-secret" not in repr(metadata)


def test_exchange_token_creation_failure_is_audited_and_reraised(app, initialized_db, tmp_path):
    config, validated = _exchange_endpoint_config(tmp_path)
    form = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": "service-account-jwt",
        "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
    }
    application = Mock(client_id="client-id")

    with (
        patch.dict(real_app.config, config),
        patch.object(KubernetesSATokenValidator, "validate", return_value=validated),
        patch.object(model.oauth, "get_canonical_bootstrap_application", return_value=application),
        patch(
            "endpoints.api.bootstrap.create_workload_identity_oauth_token",
            side_effect=RuntimeError("token-secret"),
        ),
        patch("endpoints.api.bootstrap.log_action") as audit,
        app.test_request_context(method="POST", data=form),
        pytest.raises(RuntimeError, match="token-secret"),
    ):
        _exchange_bootstrap_token()

    metadata = audit.call_args.kwargs["metadata"]
    assert metadata["failure_category"] == "issuance"
    assert metadata["failure_reason"] == "token_creation_failed"
    assert "token-secret" not in repr(metadata)
    assert "service-account-jwt" not in repr(metadata)


def test_exchange_normalizes_issuer_trailing_slashes():
    from endpoints.api.bootstrap import _normalize_exchange_issuer

    assert _normalize_exchange_issuer("https://cluster.example.com/") == (
        "https://cluster.example.com"
    )
    assert _normalize_exchange_issuer("https://cluster.example.com") == (
        "https://cluster.example.com"
    )


def test_authorize_workload_scope_normalizes_issuer_and_scope():
    from endpoints.api.bootstrap import authorize_workload_scope

    authorized_subjects = [
        {
            "ISSUER": "https://cluster.example.com",
            "SUBJECT": "system:serviceaccount:quay:operator",
            "SCOPES": "org:admin repo:read",
        }
    ]

    assert (
        authorize_workload_scope(
            authorized_subjects,
            "https://cluster.example.com/",
            "system:serviceaccount:quay:operator",
            "repo:read",
        )
        == "repo:read"
    )
    assert (
        authorize_workload_scope(
            authorized_subjects,
            "https://cluster.example.com/",
            "system:serviceaccount:quay:operator",
            "",
        )
        == "org:admin repo:read"
    )


def test_exchange_expiration_is_bounded_by_maximum():
    from endpoints.api.bootstrap import _exchange_expiration_seconds

    with patch.dict(
        real_app.config,
        {
            "KUBERNETES_SA_BOOTSTRAP_CONFIG": {"BOOTSTRAP_TOKEN_MAX_TTL": 600},
            "BOOTSTRAP_TOKEN_EXPIRATION": 3600,
        },
    ):
        assert _exchange_expiration_seconds() == 600


def test_exchange_response_returns_no_store_headers():
    from endpoints.api.bootstrap import _exchange_response

    response_body, status, headers = _exchange_response({"expires_in": 600})

    assert status == 200
    assert response_body["expires_in"] == 600
    assert headers == {"Cache-Control": "no-store", "Pragma": "no-cache"}


def _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token):
    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"
    assert model.oauth.validate_bootstrap_token(access_token, config) is not None
    assert len(model.oauth.get_bootstrap_tokens(application)) == 1
    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])


def test_renew_valid_token(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, _, _, access_token = _create_bootstrap_token(config)

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 200
    assert resp.get_json() == {"status": "rotated"}
    assert os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])

    new_access_token = _stored_access_token(config)
    assert new_access_token != access_token
    assert model.oauth.validate_bootstrap_token(new_access_token, config) is not None
    assert model.oauth.validate_bootstrap_token(access_token, config) is None


def test_renew_valid_token_writes_kubernetes_secret(app, initialized_db, tmp_path, monkeypatch):
    _patch_k8s_service_account(tmp_path, monkeypatch)
    config = _k8s_bootstrap_config(tmp_path)
    _, application, _, access_token = _create_bootstrap_token(config)
    secret = {"data": {}}
    get_secret, put_secret = _k8s_secret_handlers(secret)

    with HTTMock(get_secret, put_secret), patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 200
    assert resp.get_json() == {"status": "rotated"}
    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])

    new_access_token = _k8s_secret_access_token(secret)
    tokens = model.oauth.get_bootstrap_tokens(application)
    assert len(tokens) == 1
    assert new_access_token != access_token
    assert model.oauth.validate_bootstrap_token(new_access_token, config).id == tokens[0].id
    assert model.oauth.validate_bootstrap_token(access_token, config) is None


def test_renew_removes_stale_bootstrap_tokens_for_canonical_app_only(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    owner, application, _, access_token = _create_bootstrap_token(config)
    stale_token, stale_access_token = model.oauth.create_bootstrap_oauth_api_token(
        application,
        owner,
        "repo:read",
    )
    unmarked_token, _ = model.oauth.create_user_access_token_for_application(
        owner,
        application,
        "repo:read",
        "Bearer",
        3600,
    )

    other_owner = model.user.get_user("freshuser")
    other_application = model.oauth.create_bootstrap_application(
        model.oauth.get_bootstrap_app_name(),
        other_owner,
    )
    other_token, _ = model.oauth.create_bootstrap_oauth_api_token(
        other_application,
        other_owner,
        "repo:read",
    )

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 200

    new_access_token = _stored_access_token(config)
    tokens = model.oauth.get_bootstrap_tokens(application)
    assert len(tokens) == 1
    assert model.oauth.validate_bootstrap_token(new_access_token, config).id == tokens[0].id
    assert model.oauth.lookup_access_token_by_uuid(stale_token.uuid) is None
    assert model.oauth.validate_bootstrap_token(stale_access_token, config) is None
    assert model.oauth.lookup_access_token_by_uuid(unmarked_token.uuid) is not None
    assert model.oauth.lookup_access_token_by_uuid(other_token.uuid) is not None


def test_renew_file_write_fails_rolls_back_db_token_changes(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, old_record, access_token = _create_bootstrap_token(config)

    with (
        patch.dict(real_app.config, config),
        patch("endpoints.api.bootstrap.db_transaction", lambda: model.db.atomic()),
        patch("endpoints.api.bootstrap.write_bootstrap_token", side_effect=OSError("boom")),
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 500
    assert resp.get_json()["error_type"] == "token_rotation_failed"
    assert resp.get_json()["error_message"] == "Token rotation failed: could not write token"
    assert model.oauth.lookup_access_token_by_uuid(old_record.uuid) is not None
    assert model.oauth.validate_bootstrap_token(access_token, config) is not None
    assert len(model.oauth.get_bootstrap_tokens(application)) == 1
    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])


def test_renew_db_cleanup_failure_happens_before_file_write(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, old_record, access_token = _create_bootstrap_token(config)

    with (
        patch.dict(real_app.config, config),
        patch("endpoints.api.bootstrap.db_transaction", lambda: model.db.atomic()),
        patch(
            "endpoints.api.bootstrap.delete_bootstrap_tokens",
            side_effect=RuntimeError("cleanup failed"),
        ),
        patch("endpoints.api.bootstrap.write_bootstrap_token") as mock_write_token,
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 500
    assert resp.get_json()["error_type"] == "token_rotation_failed"
    assert resp.get_json()["error_message"] == "Token rotation failed: could not clean up tokens"
    mock_write_token.assert_not_called()
    assert model.oauth.lookup_access_token_by_uuid(old_record.uuid) is not None
    assert model.oauth.validate_bootstrap_token(access_token, config) is not None
    assert len(model.oauth.get_bootstrap_tokens(application)) == 1
    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])


def test_renew_revalidates_token_after_lock(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, _, token_record, access_token = _create_bootstrap_token(config)

    with (
        patch.dict(real_app.config, config),
        patch(
            "endpoints.api.bootstrap.validate_bootstrap_token",
            side_effect=[token_record, None],
        ),
        patch("endpoints.api.bootstrap.lock_bootstrap_token_operation") as mock_lock,
        patch("endpoints.api.bootstrap.write_bootstrap_token") as mock_write_token,
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"
    mock_lock.assert_called_once_with()
    mock_write_token.assert_not_called()


def test_renew_expired_token_rejected_before_lock(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, token_record, access_token = _create_bootstrap_token(config)
    token_record.expires_at = _expired_time()
    token_record.save()

    with (
        patch.dict(real_app.config, config),
        patch("endpoints.api.bootstrap.lock_bootstrap_token_operation") as mock_lock,
        patch("endpoints.api.bootstrap.write_bootstrap_token") as mock_write_token,
    ):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token)
    mock_lock.assert_not_called()
    mock_write_token.assert_not_called()


def test_renew_without_bearer_reaches_handler_with_valid_csrf(app, initialized_db):
    with app.test_client() as cl:
        with cl.session_transaction() as sess:
            sess["_csrf_token"] = "csrf-token"

        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={"X-CSRF-Token": "csrf-token"},
        )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"


def test_renew_without_auth_header_requires_csrf(app, initialized_db):
    with app.test_client() as cl:
        resp = cl.post("/api/v1/bootstrap/renew")

    assert resp.status_code == 403


def test_renew_basic_auth_requires_csrf(app, initialized_db):
    with app.test_client() as cl:
        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={"Authorization": "Basic dGVzdDp0ZXN0"},
        )

    assert resp.status_code == 403


def test_renew_basic_auth_reaches_handler_with_valid_csrf(app, initialized_db):
    with app.test_client() as cl:
        with cl.session_transaction() as sess:
            sess["_csrf_token"] = "csrf-token"

        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={
                "Authorization": "Basic dGVzdDp0ZXN0",
                "X-CSRF-Token": "csrf-token",
            },
        )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"


def test_renew_logged_in_session_without_bearer_uses_normal_csrf(app, initialized_db):
    with client_with_identity("devtable", app) as cl:
        resp = cl.post("/api/v1/bootstrap/renew")

    assert resp.status_code == 403


def test_renew_logged_in_session_without_bearer_reaches_handler_with_valid_csrf(
    app, initialized_db
):
    with client_with_identity("devtable", app) as cl:
        with cl.session_transaction() as sess:
            sess["_csrf_token"] = "csrf-token"

        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={"X-CSRF-Token": "csrf-token"},
        )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"


def test_renew_logged_in_session_with_bearer_uses_normal_csrf(app, initialized_db):
    with client_with_identity("devtable", app) as cl:
        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={"Authorization": "Bearer invalidtoken1234567890"},
        )

    assert resp.status_code == 403


def test_renew_logged_in_session_with_bearer_reaches_handler_with_valid_csrf(app, initialized_db):
    with client_with_identity("devtable", app) as cl:
        with cl.session_transaction() as sess:
            sess["_csrf_token"] = "csrf-token"

        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={
                "Authorization": "Bearer invalidtoken1234567890",
                "X-CSRF-Token": "csrf-token",
            },
        )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"


def test_renew_invalid_bearer_token(app, initialized_db):
    with app.test_client() as cl:
        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={"Authorization": "Bearer invalidtoken1234567890"},
        )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"


def test_renew_empty_bearer_token(app, initialized_db):
    with app.test_client() as cl:
        resp = cl.post(
            "/api/v1/bootstrap/renew",
            headers={"Authorization": "Bearer    "},
        )

    assert resp.status_code == 401
    assert resp.get_json()["error_type"] == "invalid_token"


def test_renew_non_bootstrap_bearer_token(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    owner = model.user.get_user("devtable")
    application = model.oauth.create_application(owner, "regular-app", "", "")
    _, access_token = model.oauth.create_user_access_token_for_application(
        owner,
        application,
        "repo:read",
        "Bearer",
        3600,
    )

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert resp.status_code == 403
    assert resp.get_json()["error_type"] == "insufficient_scope"


def test_renew_expired_token_accepted_with_nginx_local_header(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, token_record, access_token = _create_bootstrap_token(config)
    token_record.expires_at = _expired_time()
    token_record.save()

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    _QUAY_BOOTSTRAP_RENEWAL_LOCATION_HEADER: "local",
                },
                environ_base={"REMOTE_ADDR": "203.0.113.50"},
            )

    assert resp.status_code == 200
    assert resp.get_json() == {"status": "rotated"}
    assert os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])

    new_access_token = _stored_access_token(config)
    assert new_access_token != access_token
    assert model.oauth.validate_bootstrap_token(new_access_token, config) is not None
    assert model.oauth.validate_bootstrap_token(access_token, config) is None
    assert len(model.oauth.get_bootstrap_tokens(application)) == 1


def test_renew_expired_token_rejected_from_loopback_without_nginx_header(
    app, initialized_db, tmp_path
):
    config = _bootstrap_config(tmp_path)
    _, application, token_record, access_token = _create_bootstrap_token(config)
    token_record.expires_at = _expired_time()
    token_record.save()

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
                environ_base={"REMOTE_ADDR": "127.0.0.1"},
            )

    _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token)


def test_renew_expired_token_rejected_from_ipv6_loopback(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, token_record, access_token = _create_bootstrap_token(config)
    token_record.expires_at = _expired_time()
    token_record.save()

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
                environ_base={"REMOTE_ADDR": "::1"},
            )

    _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token)


def test_renew_expired_token_rejected_from_remote_addr(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, token_record, access_token = _create_bootstrap_token(config)
    token_record.expires_at = _expired_time()
    token_record.save()

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
                environ_base={"REMOTE_ADDR": "203.0.113.50"},
            )

    _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token)


def test_renew_expired_token_rejected_with_nginx_remote_header(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, token_record, access_token = _create_bootstrap_token(config)
    token_record.expires_at = _expired_time()
    token_record.save()

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    _QUAY_BOOTSTRAP_RENEWAL_LOCATION_HEADER: "remote",
                },
                environ_base={"REMOTE_ADDR": "127.0.0.1"},
            )

    _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token)


def test_renew_expired_token_rejects_proxy_derived_loopback(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, token_record, access_token = _create_bootstrap_token(config)
    token_record.expires_at = _expired_time()
    token_record.save()

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Forwarded-For": "127.0.0.1",
                },
                environ_base={"REMOTE_ADDR": "203.0.113.50"},
            )

    _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token)


def test_renew_expired_token_rejected_from_forwarded_loopback_unix_socket(
    app, initialized_db, tmp_path
):
    config = _bootstrap_config(tmp_path)
    _, application, token_record, access_token = _create_bootstrap_token(config)
    token_record.expires_at = _expired_time()
    token_record.save()

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Forwarded-For": "127.0.0.1",
                },
                environ_base={"REMOTE_ADDR": ""},
            )

    _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token)


def test_renew_expired_token_rejects_other_forwarding_headers(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, application, token_record, access_token = _create_bootstrap_token(config)
    token_record.expires_at = _expired_time()
    token_record.save()

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Real-IP": "127.0.0.1",
                    "Forwarded": "for=127.0.0.1",
                },
                environ_base={"REMOTE_ADDR": "203.0.113.50"},
            )

    _assert_expired_renew_rejected_without_rotation(resp, config, application, access_token)


def test_renew_valid_token_from_remote_addr(app, initialized_db, tmp_path):
    config = _bootstrap_config(tmp_path)
    _, _, _, access_token = _create_bootstrap_token(config)

    with patch.dict(real_app.config, config):
        with app.test_client() as cl:
            resp = cl.post(
                "/api/v1/bootstrap/renew",
                headers={"Authorization": f"Bearer {access_token}"},
                environ_base={"REMOTE_ADDR": "203.0.113.50"},
            )

    assert resp.status_code == 200
