# coding=utf-8

import json as py_json
import time
import unittest
import base64
import zlib

from mock import patch
from io import BytesIO
from urllib.parse import urlencode
from urllib.parse import urlparse, urlunparse, parse_qs
from datetime import datetime, timedelta

import jwt

from flask import url_for

from cryptography.hazmat.primitives import serialization
from authlib.jose import JsonWebKey

from app import app
from data import model
from data.database import ServiceKeyApprovalType
from endpoints import keyserver
from endpoints.api import api, api_bp
from endpoints.api.user import Signin
from endpoints.keyserver import jwk_with_kid
from endpoints.csrf import OAUTH_CSRF_TOKEN_NAME
from endpoints.web import web as web_bp
from endpoints.webhooks import webhooks as webhooks_bp
from endpoints.test.shared import gen_basic_auth
from initdb import setup_database_for_testing, finished_database_for_testing
from test.helpers import assert_action_logged
from util.security.token import encode_public_private_token
from util.registry.gzipinputstream import WINDOW_BUFFER_SIZE

try:
    app.register_blueprint(web_bp, url_prefix="")
except ValueError:
    # This blueprint was already registered
    pass

try:
    app.register_blueprint(webhooks_bp, url_prefix="/webhooks")
except ValueError:
    # This blueprint was already registered
    pass

try:
    app.register_blueprint(keyserver.key_server, url_prefix="")
except ValueError:
    # This blueprint was already registered
    pass

try:
    app.register_blueprint(api_bp, url_prefix="/api")
except ValueError:
    # This blueprint was already registered
    pass


CSRF_TOKEN_KEY = "_csrf_token"
CSRF_TOKEN = "123csrfforme"


class EndpointTestCase(unittest.TestCase):
    maxDiff = None

    def _add_csrf(self, without_csrf):
        parts = urlparse(without_csrf)
        query = parse_qs(parts[4])

        self._set_csrf()
        query[CSRF_TOKEN_KEY] = CSRF_TOKEN
        return urlunparse(list(parts[0:4]) + [urlencode(query)] + list(parts[5:]))

    def _set_csrf(self):
        with self.app.session_transaction() as sess:
            sess[CSRF_TOKEN_KEY] = CSRF_TOKEN
            sess[OAUTH_CSRF_TOKEN_NAME] = "someoauthtoken"

    def setUp(self):
        setup_database_for_testing(self)
        self.app = app.test_client()
        self.ctx = app.test_request_context()
        self.ctx.__enter__()

    def tearDown(self):
        finished_database_for_testing(self)
        self.ctx.__exit__(True, None, None)

    def getResponse(self, resource_name, expected_code=200, **kwargs):
        rv = self.app.get(url_for(resource_name, **kwargs))
        self.assertEqual(rv.status_code, expected_code)
        return rv.data

    def deleteResponse(self, resource_name, headers=None, expected_code=200, **kwargs):
        headers = headers or {}
        rv = self.app.delete(url_for(resource_name, **kwargs), headers=headers)
        self.assertEqual(rv.status_code, expected_code)
        return rv.data

    def deleteEmptyResponse(self, resource_name, headers=None, expected_code=204, **kwargs):
        headers = headers or {}
        rv = self.app.delete(url_for(resource_name, **kwargs), headers=headers)
        self.assertEqual(rv.status_code, expected_code)
        self.assertEqual(rv.data, b"")  # ensure response body empty
        return

    def putResponse(self, resource_name, headers=None, data=None, expected_code=200, **kwargs):
        headers = headers or {}
        data = data or {}
        rv = self.app.put(
            url_for(resource_name, **kwargs), headers=headers, data=py_json.dumps(data)
        )
        self.assertEqual(rv.status_code, expected_code)
        return rv.data

    def postResponse(
        self,
        resource_name,
        headers=None,
        data=None,
        form=None,
        with_csrf=True,
        expected_code=200,
        **kwargs,
    ):
        headers = headers or {}
        form = form or {}
        url = url_for(resource_name, **kwargs)
        if with_csrf:
            url = self._add_csrf(url)

        post_data = None
        if form:
            post_data = form
        elif data:
            post_data = py_json.dumps(data)

        rv = self.app.post(url, headers=headers, data=post_data)
        if expected_code is not None:
            self.assertEqual(rv.status_code, expected_code)

        return rv

    def login(self, username, password):
        rv = self.app.post(
            self._add_csrf(api.url_for(Signin)),
            data=py_json.dumps(dict(username=username, password=password)),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(rv.status_code, 200)


class BuildLogsTestCase(EndpointTestCase):
    build_uuid = "deadpork-dead-pork-dead-porkdeadpork"

    def test_buildlogs_invalid_build_uuid(self):
        self.login("public", "password")
        self.getResponse("web.buildlogs", build_uuid="bad_build_uuid", expected_code=400)

    def test_buildlogs_not_logged_in(self):
        self.getResponse("web.buildlogs", build_uuid=self.build_uuid, expected_code=403)

    def test_buildlogs_unauthorized(self):
        self.login("reader", "password")
        self.getResponse("web.buildlogs", build_uuid=self.build_uuid, expected_code=403)

    def test_buildlogs_logsarchived(self):
        self.login("public", "password")
        with patch("data.model.build.RepositoryBuild", logs_archived=True):
            self.getResponse("web.buildlogs", build_uuid=self.build_uuid, expected_code=403)

    def test_buildlogs_successful(self):
        self.login("public", "password")
        logs = ["log1", "log2"]
        with patch("endpoints.web.build_logs.get_log_entries", return_value=(None, logs)):
            resp = self.getResponse("web.buildlogs", build_uuid=self.build_uuid, expected_code=200)
            self.assertEqual({"logs": logs}, py_json.loads(resp))


class ArchivedLogsTestCase(EndpointTestCase):
    build_uuid = "deadpork-dead-pork-dead-porkdeadpork"

    def test_logarchive_invalid_build_uuid(self):
        self.login("public", "password")
        self.getResponse("web.logarchive", file_id="bad_build_uuid", expected_code=403)

    def test_logarchive_not_logged_in(self):
        self.getResponse("web.logarchive", file_id=self.build_uuid, expected_code=403)

    def test_logarchive_unauthorized(self):
        self.login("reader", "password")
        self.getResponse("web.logarchive", file_id=self.build_uuid, expected_code=403)

    def test_logarchive_file_not_found(self):
        self.login("public", "password")
        self.getResponse("web.logarchive", file_id=self.build_uuid, expected_code=403)

    def test_logarchive_successful(self):
        self.login("public", "password")
        data = b"my_file_stream"
        mock_file = BytesIO(zlib.compressobj(-1, zlib.DEFLATED, WINDOW_BUFFER_SIZE).compress(data))
        with patch("endpoints.web.log_archive._storage.stream_read_file", return_value=mock_file):
            self.getResponse("web.logarchive", file_id=self.build_uuid, expected_code=200)


class WebhookEndpointTestCase(EndpointTestCase):
    def test_invalid_build_trigger_webhook(self):
        self.postResponse(
            "webhooks.build_trigger_webhook", trigger_uuid="invalidtrigger", expected_code=404
        )

    def test_valid_build_trigger_webhook_invalid_auth(self):
        trigger = list(model.build.list_build_triggers("devtable", "building"))[0]
        self.postResponse(
            "webhooks.build_trigger_webhook", trigger_uuid=trigger.uuid, expected_code=403
        )

    def test_valid_build_trigger_webhook_cookie_auth(self):
        self.login("devtable", "password")

        # Cookie auth is not supported, so this should 403
        trigger = list(model.build.list_build_triggers("devtable", "building"))[0]
        self.postResponse(
            "webhooks.build_trigger_webhook", trigger_uuid=trigger.uuid, expected_code=403
        )

    def test_valid_build_trigger_webhook_missing_payload(self):
        auth_header = gen_basic_auth("devtable", "password")
        trigger = list(model.build.list_build_triggers("devtable", "building"))[0]
        self.postResponse(
            "webhooks.build_trigger_webhook",
            trigger_uuid=trigger.uuid,
            expected_code=400,
            headers={"Authorization": auth_header},
        )

    def test_valid_build_trigger_webhook_invalid_payload(self):
        auth_header = gen_basic_auth("devtable", "password")
        trigger = list(model.build.list_build_triggers("devtable", "building"))[0]
        self.postResponse(
            "webhooks.build_trigger_webhook",
            trigger_uuid=trigger.uuid,
            expected_code=400,
            headers={"Authorization": auth_header, "Content-Type": "application/json"},
            data={"invalid": "payload"},
        )


class WebEndpointTestCase(EndpointTestCase):
    def test_index(self):
        self.getResponse("web.index")

    def test_robots(self):
        self.getResponse("web.robots")

    def test_repo_view(self):
        self.getResponse("web.repository", path="devtable/simple")

    def test_unicode_repo_view(self):
        self.getResponse("web.repository", path="%E2%80%8Bcoreos/hyperkube%E2%80%8B")

    def test_org_view(self):
        self.getResponse("web.org_view", path="buynlarge")

    def test_user_view(self):
        self.getResponse("web.user_view", path="devtable")

    def test_confirm_repo_email(self):
        code = model.repository.create_email_authorization_for_repo(
            "devtable", "simple", "foo@bar.com"
        )
        self.getResponse("web.confirm_repo_email", code=code.code)

        found = model.repository.get_email_authorized_for_repo("devtable", "simple", "foo@bar.com")
        self.assertTrue(found.confirmed)

    def test_confirm_email(self):
        user = model.user.get_user("devtable")
        self.assertNotEqual(user.email, "foo@bar.com")

        confirmation_code = model.user.create_confirm_email_code(user, "foo@bar.com")
        self.getResponse("web.confirm_email", code=confirmation_code, expected_code=302)

        user = model.user.get_user("devtable")
        self.assertEqual(user.email, "foo@bar.com")

    def test_confirm_recovery(self):
        # Try for an invalid code.
        self.getResponse("web.confirm_recovery", code="someinvalidcode", expected_code=200)

        # Create a valid code and try.
        user = model.user.get_user("devtable")
        confirmation_code = model.user.create_reset_password_email_code(user.email)
        self.getResponse("web.confirm_recovery", code=confirmation_code, expected_code=302)

    def test_confirm_recovery_verified(self):
        # Create a valid code and try.
        user = model.user.get_user("devtable")
        user.verified = False
        user.save()

        confirmation_code = model.user.create_reset_password_email_code(user.email)
        self.getResponse("web.confirm_recovery", code=confirmation_code, expected_code=302)

        # Ensure the current user is the expected user and that they are verified.
        user = model.user.get_user("devtable")
        self.assertTrue(user.verified)

        self.getResponse("web.receipt", expected_code=404)  # Will 401 if no user.

    def test_request_authorization_code(self):
        # Try for an invalid client.
        self.getResponse(
            "web.request_authorization_code",
            client_id="foo",
            redirect_uri="bar",
            scope="baz",
            expected_code=404,
        )

        # Try for a valid client.
        org = model.organization.get_organization("buynlarge")
        assert org

        app = model.oauth.create_application(org, "test", "http://foo/bar", "http://foo/bar/baz")
        self.getResponse(
            "web.request_authorization_code",
            client_id=app.client_id,
            redirect_uri=app.redirect_uri,
            scope="repo:read",
            expected_code=200,
        )

    def test_build_status_badge(self):
        # Try for an invalid repository.
        self.getResponse("web.build_status_badge", repository="foo/bar", expected_code=404)

        # Try for a public repository.
        self.getResponse("web.build_status_badge", repository="public/publicrepo")

        # Try for an private repository.
        self.getResponse("web.build_status_badge", repository="devtable/simple", expected_code=404)

        # Try for an private repository with an invalid token.
        self.getResponse(
            "web.build_status_badge",
            repository="devtable/simple",
            token="sometoken",
            expected_code=404,
        )

        # Try for an private repository with a valid token.
        repository = model.repository.get_repository("devtable", "simple")
        self.getResponse(
            "web.build_status_badge", repository="devtable/simple", token=repository.badge_token
        )

    def test_attach_custom_build_trigger(self):
        self.getResponse("web.attach_custom_build_trigger", repository="foo/bar", expected_code=401)
        self.getResponse(
            "web.attach_custom_build_trigger", repository="devtable/simple", expected_code=401
        )

        self.login("freshuser", "password")
        self.getResponse(
            "web.attach_custom_build_trigger", repository="devtable/simple", expected_code=403
        )

        self.login("devtable", "password")
        self.getResponse(
            "web.attach_custom_build_trigger", repository="devtable/simple", expected_code=302
        )

    def test_redirect_to_repository(self):
        self.getResponse("web.redirect_to_repository", repository="foo/bar", expected_code=404)
        self.getResponse(
            "web.redirect_to_repository", repository="public/publicrepo", expected_code=302
        )
        self.getResponse(
            "web.redirect_to_repository", repository="devtable/simple", expected_code=403
        )

        self.login("devtable", "password")
        self.getResponse(
            "web.redirect_to_repository", repository="devtable/simple", expected_code=302
        )

    def test_redirect_to_namespace(self):
        self.getResponse("web.redirect_to_namespace", namespace="unknown", expected_code=404)
        self.getResponse("web.redirect_to_namespace", namespace="devtable", expected_code=302)
        self.getResponse("web.redirect_to_namespace", namespace="buynlarge", expected_code=302)


class OAuthTestCase(EndpointTestCase):
    def test_authorize_nologin(self):
        form = {
            "client_id": "someclient",
            "redirect_uri": "http://localhost:5000/foobar",
            "scope": "user:admin",
        }

        self.postResponse("web.authorize_application", form=form, with_csrf=True, expected_code=401)

    def test_authorize_invalidclient(self):
        self.login("devtable", "password")

        form = {
            "client_id": "someclient",
            "redirect_uri": "http://localhost:5000/foobar",
            "scope": "user:admin",
        }

        resp = self.postResponse(
            "web.authorize_application", form=form, with_csrf=True, expected_code=302
        )
        self.assertEqual(
            "http://localhost:5000/foobar?error=unauthorized_client", resp.headers["Location"]
        )

    def test_authorize_invalidscope(self):
        self.login("devtable", "password")

        form = {
            "client_id": "deadbeef",
            "redirect_uri": "http://localhost:8000/o2c.html",
            "scope": "invalid:scope",
        }

        resp = self.postResponse(
            "web.authorize_application", form=form, with_csrf=True, expected_code=302
        )
        self.assertEqual(
            "http://localhost:8000/o2c.html?error=invalid_scope", resp.headers["Location"]
        )

    def test_authorize_invalidredirecturi(self):
        self.login("devtable", "password")

        # Note: Defined in initdb.py
        form = {
            "client_id": "deadbeef",
            "redirect_uri": "http://some/invalid/uri",
            "scope": "user:admin",
        }

        self.postResponse("web.authorize_application", form=form, with_csrf=True, expected_code=400)

    def test_authorize_success(self):
        self.login("devtable", "password")

        # Note: Defined in initdb.py
        form = {
            "client_id": "deadbeef",
            "redirect_uri": "http://localhost:8000/o2c.html",
            "scope": "user:admin",
        }

        resp = self.postResponse(
            "web.authorize_application", form=form, with_csrf=True, expected_code=302
        )
        self.assertTrue("access_token=" in resp.headers["Location"])

    def test_authorize_nocsrf(self):
        self.login("devtable", "password")

        # Note: Defined in initdb.py
        form = {
            "client_id": "deadbeef",
            "redirect_uri": "http://localhost:8000/o2c.html",
            "scope": "user:admin",
        }

        self.postResponse(
            "web.authorize_application", form=form, with_csrf=False, expected_code=403
        )

    def test_authorize_nocsrf_withinvalidheader(self):
        # Note: Defined in initdb.py
        form = {
            "client_id": "deadbeef",
            "redirect_uri": "http://localhost:8000/o2c.html",
            "scope": "user:admin",
        }

        headers = dict(authorization="Some random header")
        self.postResponse(
            "web.authorize_application",
            headers=headers,
            form=form,
            with_csrf=False,
            expected_code=401,
        )

    def test_authorize_nocsrf_withbadheader(self):
        # Note: Defined in initdb.py
        form = {
            "client_id": "deadbeef",
            "redirect_uri": "http://localhost:8000/o2c.html",
            "scope": "user:admin",
        }

        headers = dict(authorization=gen_basic_auth("devtable", "invalidpassword"))
        self.postResponse(
            "web.authorize_application",
            headers=headers,
            form=form,
            with_csrf=False,
            expected_code=401,
        )

    def test_authorize_nocsrf_correctheader(self):
        # Note: Defined in initdb.py
        form = {
            "client_id": "deadbeef",
            "redirect_uri": "http://localhost:8000/o2c.html",
            "scope": "user:admin",
        }

        # Try without the client id being in the whitelist.
        headers = dict(authorization=gen_basic_auth("devtable", "password"))
        self.postResponse(
            "web.authorize_application",
            headers=headers,
            form=form,
            with_csrf=False,
            expected_code=403,
        )

        # Add the client ID to the whitelist and try again.
        app.config["DIRECT_OAUTH_CLIENTID_WHITELIST"] = ["deadbeef"]

        headers = dict(authorization=gen_basic_auth("devtable", "password"))
        resp = self.postResponse(
            "web.authorize_application",
            headers=headers,
            form=form,
            with_csrf=False,
            expected_code=302,
        )
        self.assertTrue("access_token=" in resp.headers["Location"])

    def test_authorize_nocsrf_ratelimiting(self):
        # Note: Defined in initdb.py
        form = {
            "client_id": "deadbeef",
            "redirect_uri": "http://localhost:8000/o2c.html",
            "scope": "user:admin",
        }

        # Try without the client id being in the whitelist a few times, making sure we eventually get rate limited.
        headers = dict(authorization=gen_basic_auth("devtable", "invalidpassword"))
        self.postResponse(
            "web.authorize_application",
            headers=headers,
            form=form,
            with_csrf=False,
            expected_code=401,
        )

        counter = 0
        while True:
            r = self.postResponse(
                "web.authorize_application",
                headers=headers,
                form=form,
                with_csrf=False,
                expected_code=None,
            )
            self.assertNotEqual(200, r.status_code)
            counter = counter + 1
            if counter > 5:
                self.fail("Exponential backoff did not fire")

            if r.status_code == 429:
                break


class KeyServerTestCase(EndpointTestCase):
    def _get_test_jwt_payload(self):
        return {
            "iss": "sample_service",
            "aud": keyserver.JWT_AUDIENCE,
            "exp": int(time.time()) + 60,
            "iat": int(time.time()),
            "nbf": int(time.time()),
        }

    def test_list_service_keys(self):
        # Retrieve all the keys.
        all_keys = model.service_keys.list_all_keys()
        visible_jwks = [
            jwk_with_kid(key) for key in model.service_keys.list_service_keys("sample_service")
        ]

        invisible_jwks = []
        for key in all_keys:
            is_expired = key.expiration_date and key.expiration_date <= datetime.utcnow()
            if key.service != "sample_service" or key.approval is None or is_expired:
                invisible_jwks.append(key.jwk)

        rv = self.getResponse("key_server.list_service_keys", service="sample_service")
        jwkset = py_json.loads(rv)

        # Make sure the hidden keys are not returned and the visible ones are returned.
        self.assertTrue(len(visible_jwks) > 0)
        self.assertTrue(len(invisible_jwks) > 0)
        self.assertEqual(len(visible_jwks), len(jwkset["keys"]))

        for jwk in jwkset["keys"]:
            self.assertIn(jwk, visible_jwks)
            self.assertNotIn(jwk, invisible_jwks)

    def test_get_service_key(self):
        # 200 for an approved key
        self.getResponse("key_server.get_service_key", service="sample_service", kid="kid1")

        # 409 for an unapproved key
        self.getResponse(
            "key_server.get_service_key", service="sample_service", kid="kid3", expected_code=409
        )

        # 404 for a non-existant key
        self.getResponse(
            "key_server.get_service_key", service="sample_service", kid="kid9999", expected_code=404
        )

        # 403 for an approved but expired key that is inside of the 2 week window.
        self.getResponse(
            "key_server.get_service_key", service="sample_service", kid="kid6", expected_code=403
        )

        # 404 for an approved, expired key that is outside of the 2 week window.
        self.getResponse(
            "key_server.get_service_key", service="sample_service", kid="kid7", expected_code=404
        )

    def test_put_service_key(self):
        # No Authorization header should yield a 400
        self.putResponse(
            "key_server.put_service_key", service="sample_service", kid="kid420", expected_code=400
        )

        # Mint a JWT with our test payload
        jwk = JsonWebKey.generate_key("RSA", 2048, is_private=True)
        private_pem = jwk.get_private_key().private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        payload = self._get_test_jwt_payload()
        token = jwt.encode(payload, private_pem, "RS256")

        # Invalid service name should yield a 400.
        self.putResponse(
            "key_server.put_service_key",
            service="sample service",
            kid="kid420",
            headers={
                "Authorization": "Bearer %s" % token.decode("ascii"),
                "Content-Type": "application/json",
            },
            data=jwk.as_dict(),
            expected_code=400,
        )

        # Publish a new key
        with assert_action_logged("service_key_create"):
            self.putResponse(
                "key_server.put_service_key",
                service="sample_service",
                kid="kid420",
                headers={
                    "Authorization": "Bearer %s" % token.decode("ascii"),
                    "Content-Type": "application/json",
                },
                data=jwk.as_dict(),
                expected_code=202,
            )

        # Ensure that the key exists but is unapproved.
        self.getResponse(
            "key_server.get_service_key", service="sample_service", kid="kid420", expected_code=409
        )

        # Attempt to rotate the key. Since not approved, it will fail.
        token = jwt.encode(payload, private_pem, "RS256", headers={"kid": "kid420"})
        self.putResponse(
            "key_server.put_service_key",
            service="sample_service",
            kid="kid6969",
            headers={
                "Authorization": "Bearer %s" % token.decode("ascii"),
                "Content-Type": "application/json",
            },
            data=jwk.as_dict(),
            expected_code=403,
        )

        # Approve the key.
        model.service_keys.approve_service_key(
            "kid420", ServiceKeyApprovalType.SUPERUSER, approver=1
        )

        # Rotate that new key
        with assert_action_logged("service_key_rotate"):
            token = jwt.encode(payload, private_pem, "RS256", headers={"kid": "kid420"})
            self.putResponse(
                "key_server.put_service_key",
                service="sample_service",
                kid="kid6969",
                headers={
                    "Authorization": "Bearer %s" % token.decode("ascii"),
                    "Content-Type": "application/json",
                },
                data=jwk.as_dict(),
                expected_code=200,
            )

        # Rotation should only work when signed by the previous key
        jwk = JsonWebKey.generate_key("RSA", 2048, is_private=True)
        private_pem = jwk.get_private_key().private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        token = jwt.encode(payload, private_pem, "RS256", headers={"kid": "kid420"})
        self.putResponse(
            "key_server.put_service_key",
            service="sample_service",
            kid="kid6969",
            headers={
                "Authorization": "Bearer %s" % token.decode("ascii"),
                "Content-Type": "application/json",
            },
            data=jwk.as_dict(),
            expected_code=403,
        )

    def test_attempt_delete_service_key_with_no_kid_signer(self):
        # Generate two keys, approving the first.
        private_key, _ = model.service_keys.generate_service_key(
            "sample_service", None, kid="first"
        )

        # Mint a JWT with our test payload but *no kid*.
        token = jwt.encode(
            self._get_test_jwt_payload(),
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ),
            "RS256",
            headers={},
        )

        # Using the credentials of our key, attempt to delete our unapproved key
        self.deleteResponse(
            "key_server.delete_service_key",
            headers={"Authorization": "Bearer %s" % token.decode("ascii")},
            expected_code=400,
            service="sample_service",
            kid="first",
        )

    def test_attempt_delete_service_key_with_expired_key(self):
        # Generate two keys, approving the first.
        private_key, _ = model.service_keys.generate_service_key(
            "sample_service", None, kid="first"
        )
        model.service_keys.approve_service_key(
            "first", ServiceKeyApprovalType.SUPERUSER, approver=1
        )
        model.service_keys.generate_service_key("sample_service", None, kid="second")

        # Mint a JWT with our test payload
        token = jwt.encode(
            self._get_test_jwt_payload(),
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ),
            "RS256",
            headers={"kid": "first"},
        )

        # Set the expiration of the first to now - some time.
        model.service_keys.set_key_expiration("first", datetime.utcnow() - timedelta(seconds=100))

        # Using the credentials of our second key, attempt to delete our unapproved key
        self.deleteResponse(
            "key_server.delete_service_key",
            headers={"Authorization": "Bearer %s" % token.decode("ascii")},
            expected_code=403,
            service="sample_service",
            kid="second",
        )

        # Set the expiration to the future and delete the key.
        model.service_keys.set_key_expiration("first", datetime.utcnow() + timedelta(seconds=100))

        with assert_action_logged("service_key_delete"):
            self.deleteEmptyResponse(
                "key_server.delete_service_key",
                headers={"Authorization": "Bearer %s" % token.decode("ascii")},
                expected_code=204,
                service="sample_service",
                kid="second",
            )

    def test_delete_unapproved_service_key(self):
        # No Authorization header should yield a 400
        self.deleteResponse(
            "key_server.delete_service_key", expected_code=400, service="sample_service", kid="kid1"
        )

        # Generate an unapproved key.
        private_key, _ = model.service_keys.generate_service_key(
            "sample_service", None, kid="unapprovedkeyhere"
        )

        # Mint a JWT with our test payload
        token = jwt.encode(
            self._get_test_jwt_payload(),
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ),
            "RS256",
            headers={"kid": "unapprovedkeyhere"},
        )

        # Delete our unapproved key with itself.
        with assert_action_logged("service_key_delete"):
            self.deleteEmptyResponse(
                "key_server.delete_service_key",
                headers={"Authorization": "Bearer %s" % token.decode("ascii")},
                expected_code=204,
                service="sample_service",
                kid="unapprovedkeyhere",
            )

    def test_delete_chained_service_key(self):
        # No Authorization header should yield a 400
        self.deleteResponse(
            "key_server.delete_service_key", expected_code=400, service="sample_service", kid="kid1"
        )

        # Generate two keys.
        private_key, _ = model.service_keys.generate_service_key(
            "sample_service", None, kid="kid123"
        )
        model.service_keys.generate_service_key("sample_service", None, kid="kid321")

        # Mint a JWT with our test payload
        token = jwt.encode(
            self._get_test_jwt_payload(),
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ),
            "RS256",
            headers={"kid": "kid123"},
        )

        # Using the credentials of our second key, attempt tp delete our unapproved key
        self.deleteResponse(
            "key_server.delete_service_key",
            headers={"Authorization": "Bearer %s" % token.decode("ascii")},
            expected_code=403,
            service="sample_service",
            kid="kid321",
        )

        # Approve the second key.
        model.service_keys.approve_service_key(
            "kid123", ServiceKeyApprovalType.SUPERUSER, approver=1
        )

        # Using the credentials of our approved key, delete our unapproved key
        with assert_action_logged("service_key_delete"):
            self.deleteEmptyResponse(
                "key_server.delete_service_key",
                headers={"Authorization": "Bearer %s" % token.decode("ascii")},
                expected_code=204,
                service="sample_service",
                kid="kid321",
            )

        # Attempt to delete a key signed by a key from a different service
        bad_token = jwt.encode(
            self._get_test_jwt_payload(),
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ),
            "RS256",
            headers={"kid": "kid5"},
        )
        self.deleteResponse(
            "key_server.delete_service_key",
            headers={"Authorization": "Bearer %s" % bad_token.decode("ascii")},
            expected_code=403,
            service="sample_service",
            kid="kid123",
        )

        # Delete a self-signed, approved key
        with assert_action_logged("service_key_delete"):
            self.deleteEmptyResponse(
                "key_server.delete_service_key",
                headers={"Authorization": "Bearer %s" % token.decode("ascii")},
                expected_code=204,
                service="sample_service",
                kid="kid123",
            )


if __name__ == "__main__":
    unittest.main()
