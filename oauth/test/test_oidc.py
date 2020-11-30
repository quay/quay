# pylint: disable=redefined-outer-name, unused-argument, invalid-name, missing-docstring, too-many-arguments

import json
import time
import urllib.parse

import jwt
import pytest
import requests

from httmock import urlmatch, HTTMock
from Crypto.PublicKey import RSA
from jwkest.jwk import RSAKey

from oauth.oidc import OIDCLoginService, OAuthLoginException
from util.config import URLSchemeAndHostname


@pytest.fixture(scope="module")  # Slow to generate, only do it once.
def signing_key():
    private_key = RSA.generate(2048)
    jwk = RSAKey(key=private_key.publickey()).serialize()
    return {
        "id": "somekey",
        "private_key": private_key.exportKey("PEM"),
        "jwk": jwk,
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


@pytest.fixture(params=[True, False])
def mailing_feature(request):
    return request.param


@pytest.fixture(params=[True, False])
def email_verified(request):
    return request.param


@pytest.fixture(params=[True, False])
def userinfo_supported(request):
    return request.param


@pytest.fixture(params=["someusername", "foo@bar.com", None])
def preferred_username(request):
    return request.param


@pytest.fixture()
def app_config(http_client, mailing_feature):
    return {
        "PREFERRED_URL_SCHEME": "http",
        "SERVER_HOSTNAME": "localhost",
        "FEATURE_MAILING": mailing_feature,
        "SOMEOIDC_LOGIN_CONFIG": {
            "CLIENT_ID": "foo",
            "CLIENT_SECRET": "bar",
            "SERVICE_NAME": "Some Cool Service",
            "SERVICE_ICON": "http://some/icon",
            "OIDC_SERVER": "http://fakeoidc",
            "DEBUGGING": True,
        },
        "ANOTHEROIDC_LOGIN_CONFIG": {
            "CLIENT_ID": "foo",
            "CLIENT_SECRET": "bar",
            "SERVICE_NAME": "Some Other Service",
            "SERVICE_ICON": "http://some/icon",
            "OIDC_SERVER": "http://fakeoidc",
            "LOGIN_SCOPES": ["openid"],
            "DEBUGGING": True,
        },
        "OIDCWITHPARAMS_LOGIN_CONFIG": {
            "CLIENT_ID": "foo",
            "CLIENT_SECRET": "bar",
            "SERVICE_NAME": "Some Other Service",
            "SERVICE_ICON": "http://some/icon",
            "OIDC_SERVER": "http://fakeoidc",
            "DEBUGGING": True,
            "OIDC_ENDPOINT_CUSTOM_PARAMS": {
                "authorization_endpoint": {
                    "some": "param",
                },
            },
        },
        "HTTPCLIENT": http_client,
    }


@pytest.fixture()
def oidc_service(app_config):
    return OIDCLoginService(app_config, "SOMEOIDC_LOGIN_CONFIG")


@pytest.fixture()
def another_oidc_service(app_config):
    return OIDCLoginService(app_config, "ANOTHEROIDC_LOGIN_CONFIG")


@pytest.fixture()
def oidc_withparams_service(app_config):
    return OIDCLoginService(app_config, "OIDCWITHPARAMS_LOGIN_CONFIG")


@pytest.fixture()
def discovery_content(userinfo_supported):
    return {
        "scopes_supported": ["openid", "profile", "somescope"],
        "authorization_endpoint": "http://fakeoidc/authorize",
        "token_endpoint": "http://fakeoidc/token",
        "userinfo_endpoint": "http://fakeoidc/userinfo" if userinfo_supported else None,
        "jwks_uri": "http://fakeoidc/jwks",
    }


@pytest.fixture()
def userinfo_content(preferred_username, email_verified):
    return {
        "sub": "cooluser",
        "preferred_username": preferred_username,
        "email": "foo@example.com",
        "email_verified": email_verified,
    }


@pytest.fixture()
def id_token(oidc_service, signing_key, userinfo_content, app_config):
    token_data = {
        "iss": oidc_service.config["OIDC_SERVER"],
        "aud": oidc_service.client_id(),
        "nbf": int(time.time()),
        "iat": int(time.time()),
        "exp": int(time.time() + 600),
        "sub": "cooluser",
    }

    token_data.update(userinfo_content)

    token_headers = {
        "kid": signing_key["id"],
    }

    return jwt.encode(token_data, signing_key["private_key"], "RS256", headers=token_headers)


@pytest.fixture()
def discovery_handler(discovery_content):
    @urlmatch(netloc=r"fakeoidc", path=r".+openid.+")
    def handler(_, __):
        return json.dumps(discovery_content)

    return handler


@pytest.fixture()
def authorize_handler(discovery_content):
    @urlmatch(netloc=r"fakeoidc", path=r"/authorize")
    def handler(_, request):
        parsed = urllib.parse.urlparse(request.url)
        params = urllib.parse.parse_qs(parsed.query)
        return json.dumps(
            {"authorized": True, "scope": params["scope"][0], "state": params["state"][0]}
        )

    return handler


@pytest.fixture()
def token_handler(oidc_service, id_token, valid_code):
    @urlmatch(netloc=r"fakeoidc", path=r"/token")
    def handler(_, request):
        params = urllib.parse.parse_qs(request.body)
        if params.get("redirect_uri")[0] != "http://localhost/oauth2/someoidc/callback":
            return {"status_code": 400, "content": "Invalid redirect URI"}

        if params.get("client_id")[0] != oidc_service.client_id():
            return {"status_code": 401, "content": "Invalid client id"}

        if params.get("client_secret")[0] != oidc_service.client_secret():
            return {"status_code": 401, "content": "Invalid client secret"}

        if params.get("code")[0] != valid_code:
            return {"status_code": 401, "content": "Invalid code"}

        if params.get("grant_type")[0] != "authorization_code":
            return {"status_code": 400, "content": "Invalid authorization type"}

        content = {
            "access_token": "sometoken",
            "id_token": id_token.decode("ascii"),
        }
        return {"status_code": 200, "content": json.dumps(content)}

    return handler


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
def emptykeys_jwks_handler():
    @urlmatch(netloc=r"fakeoidc", path=r"/jwks")
    def handler(_, __):
        content = {"keys": []}
        return {"status_code": 200, "content": json.dumps(content)}

    return handler


@pytest.fixture
def userinfo_handler(oidc_service, userinfo_content):
    @urlmatch(netloc=r"fakeoidc", path=r"/userinfo")
    def handler(_, req):
        if req.headers.get("Authorization") != "Bearer sometoken":
            return {"status_code": 401, "content": "Missing expected header"}

        return {"status_code": 200, "content": json.dumps(userinfo_content)}

    return handler


@pytest.fixture()
def invalidsub_userinfo_handler(oidc_service):
    @urlmatch(netloc=r"fakeoidc", path=r"/userinfo")
    def handler(_, __):
        content = {
            "sub": "invalidsub",
        }

        return {"status_code": 200, "content": json.dumps(content)}

    return handler


def test_basic_config(oidc_service):
    assert oidc_service.service_id() == "someoidc"
    assert oidc_service.service_name() == "Some Cool Service"
    assert oidc_service.get_icon() == "http://some/icon"


def test_discovery(oidc_service, http_client, discovery_content, discovery_handler):
    with HTTMock(discovery_handler):
        auth = discovery_content["authorization_endpoint"] + "?response_type=code"
        assert oidc_service.authorize_endpoint().to_url() == auth
        assert oidc_service.token_endpoint().to_url() == discovery_content["token_endpoint"]

        if discovery_content["userinfo_endpoint"] is None:
            assert oidc_service.user_endpoint() is None
        else:
            assert oidc_service.user_endpoint().to_url() == discovery_content["userinfo_endpoint"]

        assert set(oidc_service.get_login_scopes()) == set(discovery_content["scopes_supported"])


def test_discovery_with_params(
    oidc_withparams_service, http_client, discovery_content, discovery_handler
):
    with HTTMock(discovery_handler):
        assert "some=param" in oidc_withparams_service.authorize_endpoint().to_url()


def test_filtered_discovery(
    another_oidc_service, http_client, discovery_content, discovery_handler
):
    with HTTMock(discovery_handler):
        assert another_oidc_service.get_login_scopes() == ["openid"]


def test_public_config(oidc_service, discovery_handler):
    with HTTMock(discovery_handler):
        assert oidc_service.get_public_config()["OIDC"]
        assert oidc_service.get_public_config()["CLIENT_ID"] == "foo"

        assert "CLIENT_SECRET" not in oidc_service.get_public_config()
        assert "bar" not in list(oidc_service.get_public_config().values())


def test_auth_url(oidc_service, discovery_handler, http_client, authorize_handler):
    config = {"PREFERRED_URL_SCHEME": "https", "SERVER_HOSTNAME": "someserver"}

    with HTTMock(discovery_handler, authorize_handler):
        url_scheme_and_hostname = URLSchemeAndHostname.from_app_config(config)
        auth_url = oidc_service.get_auth_url(
            url_scheme_and_hostname, "", "some csrf token", ["one", "two"]
        )

        # Hit the URL and ensure it works.
        result = http_client.get(auth_url).json()
        assert result["state"] == "some csrf token"
        assert result["scope"] == "one two"


def test_exchange_code_invalidcode(
    oidc_service, discovery_handler, app_config, http_client, token_handler
):
    with HTTMock(token_handler, discovery_handler):
        with pytest.raises(OAuthLoginException):
            oidc_service.exchange_code_for_login(app_config, http_client, "testcode", "")


def test_exchange_code_invalidsub(
    oidc_service,
    discovery_handler,
    app_config,
    http_client,
    token_handler,
    invalidsub_userinfo_handler,
    jwks_handler,
    valid_code,
    userinfo_supported,
):
    # Skip when userinfo is not supported.
    if not userinfo_supported:
        return

    with HTTMock(jwks_handler, token_handler, invalidsub_userinfo_handler, discovery_handler):
        # Should fail because the sub of the user info doesn't match that returned by the id_token.
        with pytest.raises(OAuthLoginException):
            oidc_service.exchange_code_for_login(app_config, http_client, valid_code, "")


def test_exchange_code_missingkey(
    oidc_service,
    discovery_handler,
    app_config,
    http_client,
    token_handler,
    userinfo_handler,
    emptykeys_jwks_handler,
    valid_code,
):
    with HTTMock(emptykeys_jwks_handler, token_handler, userinfo_handler, discovery_handler):
        # Should fail because the key is missing.
        with pytest.raises(OAuthLoginException):
            oidc_service.exchange_code_for_login(app_config, http_client, valid_code, "")


def test_exchange_code_validcode(
    oidc_service,
    discovery_handler,
    app_config,
    http_client,
    token_handler,
    userinfo_handler,
    jwks_handler,
    valid_code,
    preferred_username,
    mailing_feature,
    email_verified,
):
    with HTTMock(jwks_handler, token_handler, userinfo_handler, discovery_handler):
        if mailing_feature and not email_verified:
            # Should fail because there isn't a verified email address.
            with pytest.raises(OAuthLoginException):
                oidc_service.exchange_code_for_login(app_config, http_client, valid_code, "")
        else:
            # Should succeed.
            lid, lusername, lemail = oidc_service.exchange_code_for_login(
                app_config, http_client, valid_code, ""
            )

            assert lid == "cooluser"

            if email_verified:
                assert lemail == "foo@example.com"
            else:
                assert lemail is None

            if preferred_username is not None:
                if preferred_username.find("@") >= 0:
                    preferred_username = preferred_username[0 : preferred_username.find("@")]

                assert lusername == preferred_username
            else:
                assert lusername == lid
