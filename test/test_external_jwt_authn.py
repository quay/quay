import base64
import unittest

from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile
from contextlib import contextmanager

import jwt
import requests

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from flask import Flask, jsonify, request, make_response

from app import app
from data.users import ExternalJWTAuthN
from initdb import setup_database_for_testing, finished_database_for_testing
from test.helpers import liveserver_app


_PORT_NUMBER = 5001


@contextmanager
def fake_jwt(requires_email=True):
    """
    Context manager which instantiates and runs a webserver with a fake JWT implementation, until
    the result is yielded.

    Usage:
    with fake_jwt() as jwt_auth:
      # Make jwt_auth requests.
    """
    jwt_app, port, public_key = _create_app(requires_email)
    server_url = "http://" + jwt_app.config["SERVER_HOSTNAME"]

    verify_url = server_url + "/user/verify"
    query_url = server_url + "/user/query"
    getuser_url = server_url + "/user/get"

    jwt_auth = ExternalJWTAuthN(
        verify_url,
        query_url,
        getuser_url,
        "authy",
        "",
        app.config["HTTPCLIENT"],
        300,
        public_key_path=public_key.name,
        requires_email=requires_email,
    )

    with liveserver_app(jwt_app, port):
        yield jwt_auth


def _generate_certs():
    public_key = NamedTemporaryFile(delete=True)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    pubkey = private_key.public_key()
    public_key.write(
        pubkey.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH,
        )
    )
    public_key.seek(0)

    return (public_key, private_pem)


def _create_app(emails=True):
    global _PORT_NUMBER
    _PORT_NUMBER = _PORT_NUMBER + 1

    public_key, private_key_data = _generate_certs()

    users = [
        {"name": "cool.user", "email": "user@domain.com", "password": "password"},
        {"name": "some.neat.user", "email": "neat@domain.com", "password": "foobar"},
        # Feature Flag: Email Blacklisting
        {"name": "blacklistedcom", "email": "foo@blacklisted.com", "password": "somepass"},
        {"name": "blacklistednet", "email": "foo@blacklisted.net", "password": "somepass"},
        {"name": "blacklistedorg", "email": "foo@blacklisted.org", "password": "somepass"},
        {"name": "notblacklistedcom", "email": "foo@notblacklisted.com", "password": "somepass"},
    ]

    jwt_app = Flask("testjwt")
    jwt_app.config["SERVER_HOSTNAME"] = "localhost:%s" % _PORT_NUMBER

    def _get_basic_auth():
        data = base64.b64decode(request.headers["Authorization"][len("Basic ") :]).decode("utf-8")
        return data.split(":", 1)

    @jwt_app.route("/user/query", methods=["GET"])
    def query_users():
        query = request.args.get("query")
        results = []

        for user in users:
            if user["name"].startswith(query):
                result = {
                    "username": user["name"],
                }

                if emails:
                    result["email"] = user["email"]

                results.append(result)

        token_data = {
            "iss": "authy",
            "aud": "quay.io/jwtauthn/query",
            "nbf": datetime.utcnow(),
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=60),
            "results": results,
        }

        encoded = jwt.encode(token_data, private_key_data, "RS256")
        return jsonify({"token": encoded.decode("ascii")})

    @jwt_app.route("/user/get", methods=["GET"])
    def get_user():
        username = request.args.get("username")

        if username == "disabled":
            return make_response("User is currently disabled", 401)

        for user in users:
            if user["name"] == username or user["email"] == username:
                token_data = {
                    "iss": "authy",
                    "aud": "quay.io/jwtauthn/getuser",
                    "nbf": datetime.utcnow(),
                    "iat": datetime.utcnow(),
                    "exp": datetime.utcnow() + timedelta(seconds=60),
                    "sub": user["name"],
                    "email": user["email"],
                }

                encoded = jwt.encode(token_data, private_key_data, "RS256")
                return jsonify({"token": encoded.decode("ascii")})

        return make_response("Invalid username or password", 404)

    @jwt_app.route("/user/verify", methods=["GET"])
    def verify_user():
        username, password = _get_basic_auth()

        if username == "disabled":
            return make_response("User is currently disabled", 401)

        for user in users:
            if user["name"] == username or user["email"] == username:
                if password != user["password"]:
                    return make_response("", 404)

                token_data = {
                    "iss": "authy",
                    "aud": "quay.io/jwtauthn",
                    "nbf": datetime.utcnow(),
                    "iat": datetime.utcnow(),
                    "exp": datetime.utcnow() + timedelta(seconds=60),
                    "sub": user["name"],
                    "email": user["email"],
                }

                encoded = jwt.encode(token_data, private_key_data, "RS256")
                return jsonify({"token": encoded.decode("ascii")})

        return make_response("Invalid username or password", 404)

    jwt_app.config["TESTING"] = True
    return jwt_app, _PORT_NUMBER, public_key


class JWTAuthTestMixin:
    """
    Mixin defining all the JWT auth tests.
    """

    maxDiff = None

    @property
    def emails(self):
        raise NotImplementedError

    def setUp(self):
        setup_database_for_testing(self)
        self.app = app.test_client()
        self.ctx = app.test_request_context()
        self.ctx.__enter__()

        self.session = requests.Session()

    def tearDown(self):
        finished_database_for_testing(self)
        self.ctx.__exit__(True, None, None)

    def test_verify_and_link_user(self):
        with fake_jwt(self.emails) as jwt_auth:
            result, error_message = jwt_auth.verify_and_link_user("invaliduser", "foobar")
            self.assertEqual("Invalid username or password", error_message)
            self.assertIsNone(result)

            result, _ = jwt_auth.verify_and_link_user("cool.user", "invalidpassword")
            self.assertIsNone(result)

            result, _ = jwt_auth.verify_and_link_user("cool.user", "password")
            self.assertIsNotNone(result)
            self.assertEqual("cool_user", result.username)

            result, _ = jwt_auth.verify_and_link_user("some.neat.user", "foobar")
            self.assertIsNotNone(result)
            self.assertEqual("some_neat_user", result.username)

    def test_confirm_existing_user(self):
        with fake_jwt(self.emails) as jwt_auth:
            # Create the users in the DB.
            result, _ = jwt_auth.verify_and_link_user("cool.user", "password")
            self.assertIsNotNone(result)

            result, _ = jwt_auth.verify_and_link_user("some.neat.user", "foobar")
            self.assertIsNotNone(result)

            # Confirm a user with the same internal and external username.
            result, _ = jwt_auth.confirm_existing_user("cool_user", "invalidpassword")
            self.assertIsNone(result)

            result, _ = jwt_auth.confirm_existing_user("cool_user", "password")
            self.assertIsNotNone(result)
            self.assertEqual("cool_user", result.username)

            # Fail to confirm the *external* username, which should return nothing.
            result, _ = jwt_auth.confirm_existing_user("some.neat.user", "password")
            self.assertIsNone(result)

            # Now confirm the internal username.
            result, _ = jwt_auth.confirm_existing_user("some_neat_user", "foobar")
            self.assertIsNotNone(result)
            self.assertEqual("some_neat_user", result.username)

    def test_disabled_user_custom_error(self):
        with fake_jwt(self.emails) as jwt_auth:
            result, error_message = jwt_auth.verify_and_link_user("disabled", "password")
            self.assertIsNone(result)
            self.assertEqual("User is currently disabled", error_message)

    def test_query(self):
        with fake_jwt(self.emails) as jwt_auth:
            # Lookup `cool`.
            results, identifier, error_message = jwt_auth.query_users("cool")
            self.assertIsNone(error_message)
            self.assertEqual("jwtauthn", identifier)
            self.assertEqual(1, len(results))

            self.assertEqual("cool.user", results[0].username)
            self.assertEqual("user@domain.com" if self.emails else None, results[0].email)

            # Lookup `some`.
            results, identifier, error_message = jwt_auth.query_users("some")
            self.assertIsNone(error_message)
            self.assertEqual("jwtauthn", identifier)
            self.assertEqual(1, len(results))

            self.assertEqual("some.neat.user", results[0].username)
            self.assertEqual("neat@domain.com" if self.emails else None, results[0].email)

            # Lookup `unknown`.
            results, identifier, error_message = jwt_auth.query_users("unknown")
            self.assertIsNone(error_message)
            self.assertEqual("jwtauthn", identifier)
            self.assertEqual(0, len(results))

    def test_get_user(self):
        with fake_jwt(self.emails) as jwt_auth:
            # Lookup cool.user.
            result, error_message = jwt_auth.get_user("cool.user")
            self.assertIsNone(error_message)
            self.assertIsNotNone(result)

            self.assertEqual("cool.user", result.username)
            self.assertEqual("user@domain.com", result.email)

            # Lookup some.neat.user.
            result, error_message = jwt_auth.get_user("some.neat.user")
            self.assertIsNone(error_message)
            self.assertIsNotNone(result)

            self.assertEqual("some.neat.user", result.username)
            self.assertEqual("neat@domain.com", result.email)

            # Lookup unknown user.
            result, error_message = jwt_auth.get_user("unknownuser")
            self.assertIsNone(result)

    def test_link_user(self):
        with fake_jwt(self.emails) as jwt_auth:
            # Link cool.user.
            user, error_message = jwt_auth.link_user("cool.user")
            self.assertIsNone(error_message)
            self.assertIsNotNone(user)
            self.assertEqual("cool_user", user.username)

            # Link again. Should return the same user record.
            user_again, _ = jwt_auth.link_user("cool.user")
            self.assertEqual(user_again.id, user.id)

            # Confirm cool.user.
            result, _ = jwt_auth.confirm_existing_user("cool_user", "password")
            self.assertIsNotNone(result)
            self.assertEqual("cool_user", result.username)

    def test_link_invalid_user(self):
        with fake_jwt(self.emails) as jwt_auth:
            user, error_message = jwt_auth.link_user("invaliduser")
            self.assertIsNotNone(error_message)
            self.assertIsNone(user)


class JWTAuthNoEmailTestCase(JWTAuthTestMixin, unittest.TestCase):
    """
    Test cases for JWT auth, with emails disabled.
    """

    @property
    def emails(self):
        return False


class JWTAuthTestCase(JWTAuthTestMixin, unittest.TestCase):
    """
    Test cases for JWT auth, with emails enabled.
    """

    @property
    def emails(self):
        return True


if __name__ == "__main__":
    unittest.main()
