import json as py_json
import time
import unittest
import urllib.parse

import jwt

from Crypto.PublicKey import RSA
from httmock import urlmatch, HTTMock
from jwkest.jwk import RSAKey

from app import app, authentication
from data import model
from endpoints.oauth.login import oauthlogin as oauthlogin_bp
from test.test_endpoints import EndpointTestCase
from test.test_ldap import mock_ldap


class AuthForTesting(object):
    def __init__(self, auth_engine):
        self.auth_engine = auth_engine
        self.existing_state = None

    def __enter__(self):
        self.existing_state = authentication.state
        authentication.state = self.auth_engine

    def __exit__(self, type, value, traceback):
        authentication.state = self.existing_state


try:
    app.register_blueprint(oauthlogin_bp, url_prefix="/oauth2")
except ValueError:
    # This blueprint was already registered
    pass


class OAuthLoginTestCase(EndpointTestCase):
    def invoke_oauth_tests(
        self,
        callback_endpoint,
        attach_endpoint,
        service_name,
        service_ident,
        new_username,
        test_attach=True,
    ):
        # Test callback.
        created = self.invoke_oauth_test(
            callback_endpoint, service_name, service_ident, new_username
        )

        # Delete the created user.
        self.assertNotEqual(created.username, "devtable")
        model.user.delete_user(created, [])

        # Test attach.
        if test_attach:
            self.login("devtable", "password")
            self.invoke_oauth_test(attach_endpoint, service_name, service_ident, "devtable")

    def invoke_oauth_test(self, endpoint_name, service_name, service_ident, username):
        self._set_csrf()

        # No CSRF.
        self.getResponse("oauthlogin." + endpoint_name, expected_code=403)

        # Invalid CSRF.
        self.getResponse("oauthlogin." + endpoint_name, state="somestate", expected_code=403)

        # Valid CSRF, invalid code.
        self.getResponse(
            "oauthlogin." + endpoint_name,
            state="someoauthtoken",
            code="invalidcode",
            expected_code=400,
        )

        # Valid CSRF, valid code.
        self.getResponse(
            "oauthlogin." + endpoint_name,
            state="someoauthtoken",
            code="somecode",
            expected_code=302,
        )

        # Ensure the user was added/modified.
        found_user = model.user.get_user(username)
        self.assertIsNotNone(found_user)

        federated_login = model.user.lookup_federated_login(found_user, service_name)
        self.assertIsNotNone(federated_login)
        self.assertEqual(federated_login.service_ident, service_ident)
        return found_user

    def test_google_oauth(self):
        @urlmatch(netloc=r"accounts.google.com", path="/o/oauth2/token")
        def account_handler(_, request):
            parsed = dict(urllib.parse.parse_qsl(request.body))
            if parsed["code"] == "somecode":
                content = {"access_token": "someaccesstoken"}
                return py_json.dumps(content)
            else:
                return {"status_code": 400, "content": '{"message": "Invalid code"}'}

        @urlmatch(netloc=r"www.googleapis.com", path="/oauth2/v1/userinfo")
        def user_handler(_, __):
            content = {
                "id": "someid",
                "email": "someemail@example.com",
                "verified_email": True,
            }
            return py_json.dumps(content)

        with HTTMock(account_handler, user_handler):
            self.invoke_oauth_tests(
                "google_oauth_callback", "google_oauth_attach", "google", "someid", "someemail"
            )

    def test_github_oauth(self):
        @urlmatch(netloc=r"github.com", path="/login/oauth/access_token")
        def account_handler(url, _):
            parsed = dict(urllib.parse.parse_qsl(url.query))
            if parsed["code"] == "somecode":
                content = {"access_token": "someaccesstoken"}
                return py_json.dumps(content)
            else:
                return {"status_code": 400, "content": '{"message": "Invalid code"}'}

        @urlmatch(netloc=r"github.com", path="/api/v3/user")
        def user_handler(_, __):
            content = {"id": "someid", "login": "someusername"}
            return py_json.dumps(content)

        @urlmatch(netloc=r"github.com", path="/api/v3/user/emails")
        def email_handler(_, __):
            content = [
                {
                    "email": "someemail@example.com",
                    "verified": True,
                    "primary": True,
                }
            ]
            return py_json.dumps(content)

        with HTTMock(account_handler, email_handler, user_handler):
            self.invoke_oauth_tests(
                "github_oauth_callback", "github_oauth_attach", "github", "someid", "someusername"
            )

    def _get_oidc_mocks(self):
        private_key = RSA.generate(2048)
        generatedjwk = RSAKey(key=private_key.publickey()).serialize()
        kid = "somekey"
        private_pem = private_key.exportKey("PEM")

        token_data = {
            "iss": app.config["TESTOIDC_LOGIN_CONFIG"]["OIDC_SERVER"],
            "aud": app.config["TESTOIDC_LOGIN_CONFIG"]["CLIENT_ID"],
            "nbf": int(time.time()),
            "iat": int(time.time()),
            "exp": int(time.time() + 600),
            "sub": "cool.user",
        }

        token_headers = {
            "kid": kid,
        }

        id_token = jwt.encode(token_data, private_pem, "RS256", headers=token_headers)

        @urlmatch(netloc=r"fakeoidc", path="/token")
        def token_handler(_, request):
            if request.body.find("code=somecode") >= 0:
                content = {"access_token": "someaccesstoken", "id_token": id_token.decode("ascii")}
                return py_json.dumps(content)
            else:
                return {"status_code": 400, "content": '{"message": "Invalid code"}'}

        @urlmatch(netloc=r"fakeoidc", path="/user")
        def user_handler(_, __):
            content = {
                "sub": "cool.user",
                "preferred_username": "someusername",
                "email": "someemail@example.com",
                "email_verified": True,
            }
            return py_json.dumps(content)

        @urlmatch(netloc=r"fakeoidc", path="/jwks")
        def jwks_handler(_, __):
            jwk = generatedjwk.copy()
            jwk.update({"kid": kid})

            content = {"keys": [jwk]}
            return py_json.dumps(content)

        @urlmatch(netloc=r"fakeoidc", path=".+openid.+")
        def discovery_handler(_, __):
            content = {
                "scopes_supported": ["profile"],
                "authorization_endpoint": "http://fakeoidc/authorize",
                "token_endpoint": "http://fakeoidc/token",
                "userinfo_endpoint": "http://fakeoidc/userinfo",
                "jwks_uri": "http://fakeoidc/jwks",
            }
            return py_json.dumps(content)

        return (discovery_handler, jwks_handler, token_handler, user_handler)

    def test_oidc_database_auth(self):
        oidc_mocks = self._get_oidc_mocks()
        with HTTMock(*oidc_mocks):
            self.invoke_oauth_tests(
                "testoidc_oauth_callback",
                "testoidc_oauth_attach",
                "testoidc",
                "cool.user",
                "someusername",
            )

    def test_oidc_ldap_auth(self):
        # Test with database auth.
        oidc_mocks = self._get_oidc_mocks()
        with mock_ldap() as ldap:
            with AuthForTesting(ldap):
                with HTTMock(*oidc_mocks):
                    self.invoke_oauth_tests(
                        "testoidc_oauth_callback",
                        "testoidc_oauth_attach",
                        "testoidc",
                        "cool.user",
                        "cool_user",
                        test_attach=False,
                    )


if __name__ == "__main__":
    unittest.main()
