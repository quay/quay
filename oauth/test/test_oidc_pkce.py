# pylint: disable=missing-docstring, unused-argument, redefined-outer-name

import json
import time
import urllib.parse

import jwt
import pytest
import requests
from authlib.jose import JsonWebKey
from cryptography.hazmat.primitives import serialization
from httmock import HTTMock, urlmatch

from oauth.oidc import OIDCLoginService
from test import fixtures as _fixtures  # ensure application/DB fixtures load early


@pytest.fixture(scope="module")
def signing_key():
    jwk = JsonWebKey.generate_key("RSA", 2048, is_private=True)
    return {
        "id": "somekey",
        "private_key": jwk.get_private_key().private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        "jwk": jwk.as_dict(),
    }


@pytest.fixture(scope="module")
def http_client():
    sess = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)
    return sess


@pytest.fixture(scope="module")
def valid_code():
    return "validcode"


@pytest.fixture()
def app_config(http_client):
    return {
        "PREFERRED_URL_SCHEME": "http",
        "SERVER_HOSTNAME": "localhost",
        "PKCEOIDC_LOGIN_CONFIG": {
            "CLIENT_ID": "foo",
            "CLIENT_SECRET": "bar",
            "SERVICE_NAME": "PKCE Service",
            "OIDC_SERVER": "http://fakeoidc",
            "DEBUGGING": True,
            "USE_PKCE": True,
            "PKCE_METHOD": "S256",
        },
        "PUBLICPKCEOIDC_LOGIN_CONFIG": {
            "CLIENT_ID": "foo",
            "CLIENT_SECRET": "bar",
            "SERVICE_NAME": "PKCE Public Service",
            "OIDC_SERVER": "http://fakeoidc",
            "DEBUGGING": True,
            "USE_PKCE": True,
            "PKCE_METHOD": "S256",
            "PUBLIC_CLIENT": True,
        },
        "PLAINPKCEOIDC_LOGIN_CONFIG": {
            "CLIENT_ID": "foo",
            "CLIENT_SECRET": "bar",
            "SERVICE_NAME": "PKCE Plain Service",
            "OIDC_SERVER": "http://fakeoidc",
            "DEBUGGING": True,
            "USE_PKCE": True,
            "PKCE_METHOD": "plain",
        },
        "HTTPCLIENT": http_client,
        "TESTING": True,
    }


@pytest.fixture()
def pkce_oidc_service(app_config):
    return OIDCLoginService(app_config, "PKCEOIDC_LOGIN_CONFIG")


@pytest.fixture()
def public_pkce_oidc_service(app_config):
    return OIDCLoginService(app_config, "PUBLICPKCEOIDC_LOGIN_CONFIG")


@pytest.fixture()
def plain_pkce_oidc_service(app_config):
    return OIDCLoginService(app_config, "PLAINPKCEOIDC_LOGIN_CONFIG")


@pytest.fixture()
def discovery_content():
    return {
        "scopes_supported": ["openid", "profile", "somescope"],
        "authorization_endpoint": "http://fakeoidc/authorize",
        "token_endpoint": "http://fakeoidc/token",
        "userinfo_endpoint": "http://fakeoidc/userinfo",
        "jwks_uri": "http://fakeoidc/jwks",
    }


@pytest.fixture()
def discovery_handler(discovery_content):
    @urlmatch(netloc=r"fakeoidc", path=r".+openid.+")
    def handler(_, __):
        return json.dumps(discovery_content)

    return handler


@pytest.fixture()
def id_token(pkce_oidc_service, signing_key):
    token_data = {
        "iss": pkce_oidc_service.config["OIDC_SERVER"],
        "aud": pkce_oidc_service.client_id(),
        "nbf": int(time.time()),
        "iat": int(time.time()),
        "exp": int(time.time() + 600),
        "sub": "cooluser",
        "email": "foo@example.com",
        "email_verified": True,
    }

    token_headers = {"kid": signing_key["id"]}
    return jwt.encode(token_data, signing_key["private_key"], "RS256", headers=token_headers)


@pytest.fixture()
def jwks_handler(signing_key):
    def jwk_with_kid(kid, jwk):
        jwk = jwk.copy()
        jwk.update({"kid": kid})
        return jwk

    @urlmatch(netloc=r"fakeoidc", path=r"/jwks")
    def handler(_, __):
        content = {"keys": [jwk_with_kid(signing_key["id"], signing_key["jwk"])]}
        return {"status_code": 200, "content": json.dumps(content)}

    return handler


@pytest.fixture()
def userinfo_handler():
    @urlmatch(netloc=r"fakeoidc", path=r"/userinfo")
    def handler(_, req):
        if req.headers.get("Authorization") != "Bearer sometoken":
            return {"status_code": 401, "content": "Missing expected header"}
        content = {"sub": "cooluser", "email": "foo@example.com", "email_verified": True}
        return {"status_code": 200, "content": json.dumps(content)}

    return handler


@pytest.fixture()
def token_handler_pkce(id_token, valid_code):
    @urlmatch(netloc=r"fakeoidc", path=r"/token")
    def handler(_, request):
        params = urllib.parse.parse_qs(request.body)
        if params.get("code")[0] != valid_code:
            return {"status_code": 401, "content": "Invalid code"}
        if params.get("grant_type")[0] != "authorization_code":
            return {"status_code": 400, "content": "Invalid authorization type"}
        if not params.get("code_verifier"):
            return {"status_code": 400, "content": "Missing code_verifier"}
        content = {"access_token": "sometoken", "id_token": id_token}
        return {"status_code": 200, "content": json.dumps(content)}

    return handler


@pytest.fixture()
def token_handler_public_pkce(id_token, valid_code):
    @urlmatch(netloc=r"fakeoidc", path=r"/token")
    def handler(_, request):
        params = urllib.parse.parse_qs(request.body)
        if "client_secret" in params:
            return {"status_code": 400, "content": "client_secret should not be sent"}
        if params.get("code")[0] != valid_code:
            return {"status_code": 401, "content": "Invalid code"}
        if params.get("grant_type")[0] != "authorization_code":
            return {"status_code": 400, "content": "Invalid authorization type"}
        if not params.get("code_verifier"):
            return {"status_code": 400, "content": "Missing code_verifier"}
        content = {"access_token": "sometoken", "id_token": id_token}
        return {"status_code": 200, "content": json.dumps(content)}

    return handler


def test_pkce_token_exchange_includes_verifier(
    pkce_oidc_service,
    discovery_handler,
    app_config,
    http_client,
    token_handler_pkce,
    userinfo_handler,
    jwks_handler,
    valid_code,
):
    with HTTMock(jwks_handler, token_handler_pkce, userinfo_handler, discovery_handler):
        id_tok, access_tok = pkce_oidc_service.exchange_code_for_tokens(
            app_config, http_client, valid_code, "", code_verifier="test-verifier"
        )
        assert access_tok == "sometoken"
        assert id_tok is not None


def test_public_client_omits_client_secret(
    public_pkce_oidc_service,
    discovery_handler,
    app_config,
    http_client,
    token_handler_public_pkce,
    userinfo_handler,
    jwks_handler,
    valid_code,
):
    with HTTMock(jwks_handler, token_handler_public_pkce, userinfo_handler, discovery_handler):
        id_tok, access_tok = public_pkce_oidc_service.exchange_code_for_tokens(
            app_config, http_client, valid_code, "", code_verifier="test-verifier"
        )
        assert access_tok == "sometoken"
        assert id_tok is not None


def test_pkce_missing_verifier_fails(
    pkce_oidc_service,
    discovery_handler,
    app_config,
    http_client,
    token_handler_pkce,
    userinfo_handler,
    jwks_handler,
    valid_code,
):
    # Without code_verifier, PKCE-enabled flow should fail against a server requiring it
    from oauth.login import OAuthLoginException

    with HTTMock(jwks_handler, token_handler_pkce, userinfo_handler, discovery_handler):
        with pytest.raises(OAuthLoginException):
            pkce_oidc_service.exchange_code_for_tokens(app_config, http_client, valid_code, "")


def test_pkce_plain_method_succeeds(
    plain_pkce_oidc_service,
    discovery_handler,
    app_config,
    http_client,
    token_handler_pkce,
    userinfo_handler,
    jwks_handler,
    valid_code,
):
    # With PKCE_METHOD=plain, token exchange should still succeed when code_verifier provided
    with HTTMock(jwks_handler, token_handler_pkce, userinfo_handler, discovery_handler):
        id_tok, access_tok = plain_pkce_oidc_service.exchange_code_for_tokens(
            app_config, http_client, valid_code, "", code_verifier="plain-verifier"
        )
        assert access_tok == "sometoken"
        assert id_tok is not None
