from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from auth.kubernetes_sa import (
    OIDC_WELL_KNOWN,
    KubernetesSATokenValidationError,
    KubernetesSATokenValidator,
)

ISSUER = "https://kubernetes.default.svc"
AUDIENCE = "quay-bootstrap"
KID = "test-key"
NAMESPACE = "quay-operator"
SA_NAME = "controller-manager"
SA_UID = "72bcb00a-38f0-4b1a-9b8e-1f6c3a2d9e11"
SUBJECT = f"system:serviceaccount:{NAMESPACE}:{SA_NAME}"


def _rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _jwk(
    private_key,
    kid=KID,
    use: str | None = "sig",
    alg: str | None = "RS256",
    kty: str | None = "RSA",
):
    public_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    public_jwk["kid"] = kid
    if use is not None:
        public_jwk["use"] = use
    if alg is not None:
        public_jwk["alg"] = alg
    if kty is not None:
        public_jwk["kty"] = kty
    return public_jwk


def _discovery_response(jwks_uri=None, issuer=ISSUER, status_code=200):
    return Mock(
        status_code=status_code,
        json=Mock(
            return_value={"issuer": issuer, "jwks_uri": jwks_uri or f"{ISSUER}/openid/v1/jwks"}
        ),
    )


def _jwks_response(keys, status_code=200):
    return Mock(status_code=status_code, json=Mock(return_value={"keys": keys}))


def _sequence(*responses):
    """Returns each response in order, then repeats the last one indefinitely.

    An item may be an Exception instance, which is raised instead of returned.
    """
    remaining = list(responses)

    def _next():
        item = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        if isinstance(item, Exception):
            raise item
        return item

    return _next


def _dispatching_client(discovery_fn, jwks_fn):
    def get(url, **_kwargs):
        if url.endswith(OIDC_WELL_KNOWN):
            return discovery_fn()
        return jwks_fn()

    client = Mock()
    client.get.side_effect = get
    return client


def _validator(private_key, discovery_fn=None, jwks_fn=None, **config_overrides):
    if discovery_fn is None:
        discovery_fn = _sequence(_discovery_response())
    if jwks_fn is None:
        jwks_fn = _sequence(_jwks_response([_jwk(private_key)]))
    client = _dispatching_client(discovery_fn, jwks_fn)
    config = {
        "ISSUERS": [{"ISSUER": ISSUER}],
        "REQUIRED_AUDIENCE": AUDIENCE,
        **config_overrides,
    }
    return KubernetesSATokenValidator(config, client), client


def _token(private_key, kid=KID, no_kid=False, **claim_overrides):
    now = datetime.now(UTC)
    claims = {
        "iss": ISSUER,
        "sub": SUBJECT,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=10),
        "kubernetes.io": {
            "namespace": NAMESPACE,
            "serviceaccount": {"name": SA_NAME, "uid": SA_UID},
        },
        **claim_overrides,
    }
    headers = {} if no_kid else {"kid": kid}
    return jwt.encode(claims, private_key, algorithm="RS256", headers=headers)


def test_validates_service_account_token_and_refetches_oidc_data():
    private_key = _rsa_key()
    validator, client = _validator(private_key)

    first = validator.validate(_token(private_key))
    second = validator.validate(_token(private_key))

    assert first.issuer == ISSUER
    assert first.subject == SUBJECT
    assert first.claims["sub"] == SUBJECT
    assert second.subject == SUBJECT
    assert client.get.call_count == 4


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://untrusted.example.com"},
        {"aud": "another-service"},
        {"exp": datetime.now(UTC) - timedelta(minutes=1)},
        {"nbf": datetime.now(UTC) + timedelta(minutes=5)},
        {"sub": "ordinary-user"},
        {"sub": "system:serviceaccount:onlyonepart"},
        {
            "kubernetes.io": {
                "namespace": "wrong-namespace",
                "serviceaccount": {"name": SA_NAME, "uid": SA_UID},
            }
        },
        {
            "kubernetes.io": {
                "namespace": NAMESPACE,
                "serviceaccount": {"name": "wrong-name", "uid": SA_UID},
            }
        },
        {"kubernetes.io": {"namespace": NAMESPACE, "serviceaccount": {"name": SA_NAME, "uid": ""}}},
        {"kubernetes.io": {"namespace": NAMESPACE}},
        {"kubernetes.io": None},
    ],
)
def test_rejects_untrusted_or_invalid_claims(overrides):
    private_key = _rsa_key()
    validator, _ = _validator(private_key)

    with pytest.raises(KubernetesSATokenValidationError):
        validator.validate(_token(private_key, **overrides))


def test_rejects_missing_iat_or_exp():
    private_key = _rsa_key()
    validator, _ = _validator(private_key)

    token = jwt.encode(
        {
            "iss": ISSUER,
            "sub": SUBJECT,
            "aud": AUDIENCE,
            "kubernetes.io": {
                "namespace": NAMESPACE,
                "serviceaccount": {"name": SA_NAME, "uid": SA_UID},
            },
        },
        private_key,
        algorithm="RS256",
        headers={"kid": KID},
    )

    with pytest.raises(KubernetesSATokenValidationError):
        validator.validate(token)


def test_rejects_malformed_token():
    private_key = _rsa_key()
    validator, _ = _validator(private_key)

    with pytest.raises(KubernetesSATokenValidationError):
        validator.validate("not-a-jwt")


def test_rejects_token_missing_kid():
    private_key = _rsa_key()
    validator, client = _validator(private_key)

    token = _token(private_key, no_kid=True)
    assert "kid" not in jwt.get_unverified_header(token)

    with pytest.raises(KubernetesSATokenValidationError):
        validator.validate(token)
    assert client.get.call_count == 0


def test_uses_discovery_endpoint_ca_and_mounted_bearer_token(tmp_path):
    private_key = _rsa_key()
    bearer_path = tmp_path / "token"
    bearer_path.write_text("mounted-token\n")
    ca_path = str(tmp_path / "ca.crt")
    discovery_endpoint = "https://api.cluster.example.com:6443"
    issuer_config = {
        "ISSUER": ISSUER,
        "DISCOVERY_ENDPOINT": discovery_endpoint,
        "CA_CERT_PATH": ca_path,
        "BEARER_TOKEN_PATH": str(bearer_path),
    }
    validator, client = _validator(
        private_key,
        discovery_fn=_sequence(
            _discovery_response(jwks_uri=f"{discovery_endpoint}/openid/v1/jwks")
        ),
        ISSUERS=[issuer_config],
    )

    validator.validate(_token(private_key))

    first_call, second_call = client.get.call_args_list
    assert first_call.args[0] == f"{discovery_endpoint}/.well-known/openid-configuration"
    assert first_call.kwargs["verify"] == ca_path
    assert first_call.kwargs["headers"] == {"Authorization": "Bearer mounted-token"}
    assert first_call.kwargs["allow_redirects"] is False

    assert second_call.args[0] == f"{discovery_endpoint}/openid/v1/jwks"
    assert second_call.kwargs["allow_redirects"] is False


def test_rejects_jwks_uri_outside_discovery_origin():
    private_key = _rsa_key()
    validator, _ = _validator(
        private_key,
        discovery_fn=_sequence(_discovery_response(jwks_uri="https://attacker.example.com/jwks")),
    )

    with pytest.raises(KubernetesSATokenValidationError):
        validator.validate(_token(private_key))


def test_rejects_non_https_jwks_uri():
    private_key = _rsa_key()
    validator, _ = _validator(
        private_key,
        discovery_fn=_sequence(
            _discovery_response(jwks_uri="http://kubernetes.default.svc/openid/v1/jwks")
        ),
    )

    with pytest.raises(KubernetesSATokenValidationError):
        validator.validate(_token(private_key))


def test_rejects_discovery_issuer_mismatch():
    private_key = _rsa_key()
    validator, _ = _validator(
        private_key,
        discovery_fn=_sequence(_discovery_response(issuer="https://other-cluster.example.com")),
    )

    with pytest.raises(KubernetesSATokenValidationError):
        validator.validate(_token(private_key))


@pytest.mark.parametrize(
    "bad_jwk_overrides",
    [
        {"kty": "EC"},
        {"use": "enc"},
        {"alg": "RS384"},
    ],
)
def test_filters_out_untrusted_jwks(bad_jwk_overrides):
    private_key = _rsa_key()
    bad_jwk = _jwk(private_key, **bad_jwk_overrides)
    validator, _ = _validator(private_key, jwks_fn=_sequence(_jwks_response([bad_jwk])))

    with pytest.raises(KubernetesSATokenValidationError):
        validator.validate(_token(private_key))


def test_accepts_jwk_with_absent_use_and_alg():
    private_key = _rsa_key()
    jwk = _jwk(private_key, use=None, alg=None)
    validator, _ = _validator(private_key, jwks_fn=_sequence(_jwks_response([jwk])))

    result = validator.validate(_token(private_key))
    assert result.subject == SUBJECT


def test_discovery_request_failure_raises():
    private_key = _rsa_key()
    validator, _ = _validator(
        private_key, discovery_fn=_sequence(_discovery_response(status_code=503))
    )

    with pytest.raises(KubernetesSATokenValidationError):
        validator.validate(_token(private_key))


def test_jwks_invalid_json_raises():
    private_key = _rsa_key()
    bad_response = Mock(status_code=200, json=Mock(side_effect=ValueError("bad json")))
    validator, _ = _validator(private_key, jwks_fn=_sequence(bad_response))

    with pytest.raises(KubernetesSATokenValidationError):
        validator.validate(_token(private_key))


def test_missing_bearer_token_file_raises(tmp_path):
    private_key = _rsa_key()
    issuer_config = {
        "ISSUER": ISSUER,
        "CA_CERT_PATH": str(tmp_path / "ca.crt"),
        "BEARER_TOKEN_PATH": str(tmp_path / "missing-token"),
    }
    validator, _ = _validator(private_key, ISSUERS=[issuer_config])

    with pytest.raises(KubernetesSATokenValidationError):
        validator.validate(_token(private_key))


def test_untrusted_issuer_is_rejected_without_network_call():
    private_key = _rsa_key()
    validator, client = _validator(private_key)

    other_key = _rsa_key()
    now = datetime.now(UTC)
    other_token = jwt.encode(
        {
            "iss": "https://untrusted.example.com",
            "sub": SUBJECT,
            "aud": AUDIENCE,
            "iat": now,
            "exp": now + timedelta(minutes=10),
            "kubernetes.io": {
                "namespace": NAMESPACE,
                "serviceaccount": {"name": SA_NAME, "uid": SA_UID},
            },
        },
        other_key,
        algorithm="RS256",
        headers={"kid": KID},
    )

    with pytest.raises(KubernetesSATokenValidationError):
        validator.validate(other_token)
    assert client.get.call_count == 0


def test_each_validation_fetches_current_discovery_and_jwks():
    private_key = _rsa_key()
    second_key = _rsa_key()
    jwks_fn = _sequence(
        _jwks_response([_jwk(private_key)]),
        _jwks_response([_jwk(second_key, kid="second-key")]),
    )
    validator, client = _validator(private_key, jwks_fn=jwks_fn)

    validator.validate(_token(private_key))
    result = validator.validate(_token(second_key, kid="second-key"))

    assert result.subject == SUBJECT
    assert client.get.call_count == 4


def test_refresh_failure_rejects_instead_of_using_previous_keys():
    private_key = _rsa_key()
    jwks_fn = _sequence(
        _jwks_response([_jwk(private_key)]),
        Mock(status_code=503, json=Mock(return_value={})),
    )
    validator, _ = _validator(private_key, jwks_fn=jwks_fn)

    validator.validate(_token(private_key))
    with pytest.raises(KubernetesSATokenValidationError):
        validator.validate(_token(private_key))


def test_rotated_key_no_longer_published_fails_closed():
    private_key = _rsa_key()
    new_key = _rsa_key()
    jwks_fn = _sequence(
        _jwks_response([_jwk(private_key)]),
        _jwks_response([_jwk(new_key, kid="new-key")]),
    )
    validator, _ = _validator(private_key, jwks_fn=jwks_fn)

    validator.validate(_token(private_key))
    with pytest.raises(KubernetesSATokenValidationError):
        validator.validate(_token(private_key))


def test_unknown_kid_fails_closed_when_current_jwks_does_not_contain_it():
    private_key = _rsa_key()
    unknown_key = _rsa_key()
    validator, client = _validator(private_key)

    with pytest.raises(KubernetesSATokenValidationError):
        validator.validate(_token(unknown_key, kid="never-seen"))

    assert client.get.call_count == 2


def test_signature_failure_fetches_current_oidc_data_once():
    private_key = _rsa_key()
    forged_key = _rsa_key()
    validator, client = _validator(private_key)

    with pytest.raises(KubernetesSATokenValidationError):
        validator.validate(_token(forged_key, kid=KID))

    assert client.get.call_count == 2


def test_never_logs_bearer_token_or_jwt(tmp_path, caplog):
    private_key = _rsa_key()
    bearer_path = tmp_path / "token"
    bearer_path.write_text("super-secret-mounted-token\n")
    ca_path = tmp_path / "ca.crt"
    ca_path.write_text("fake-ca")
    issuer_config = {
        "ISSUER": ISSUER,
        "CA_CERT_PATH": str(ca_path),
        "BEARER_TOKEN_PATH": str(bearer_path),
    }
    validator, _ = _validator(private_key, ISSUERS=[issuer_config])

    with caplog.at_level("DEBUG"):
        token = _token(private_key)
        validator.validate(token)
        unknown_key = _rsa_key()
        try:
            validator.validate(_token(unknown_key, kid="unknown"))
        except KubernetesSATokenValidationError:
            pass

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "super-secret-mounted-token" not in log_text
    assert token not in log_text
