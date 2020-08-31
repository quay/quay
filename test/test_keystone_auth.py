import json
import os
import unittest

import requests

from flask import Flask, request, abort, make_response
from contextlib import contextmanager

from test.helpers import liveserver_app
from data.users.keystone import get_keystone_users
from initdb import setup_database_for_testing, finished_database_for_testing

_PORT_NUMBER = 5001


@contextmanager
def fake_keystone(version=3, requires_email=True):
    """
    Context manager which instantiates and runs a webserver with a fake Keystone implementation,
    until the result is yielded.

    Usage:
    with fake_keystone(version) as keystone_auth:
      # Make keystone_auth requests.
    """
    keystone_app, port = _create_app(requires_email)
    server_url = "http://" + keystone_app.config["SERVER_HOSTNAME"]
    endpoint_url = server_url + "/v3"
    if version == 2:
        endpoint_url = server_url + "/v2.0/auth"

    keystone_auth = get_keystone_users(
        version,
        endpoint_url,
        "adminuser",
        "adminpass",
        "admintenant",
        requires_email=requires_email,
    )
    with liveserver_app(keystone_app, port):
        yield keystone_auth


def _create_app(requires_email=True):
    global _PORT_NUMBER
    _PORT_NUMBER = _PORT_NUMBER + 1

    server_url = "http://localhost:%s" % (_PORT_NUMBER)

    users = [
        {"username": "adminuser", "name": "Admin User", "password": "adminpass"},
        {"username": "cool.user", "name": "Cool User", "password": "password"},
        {"username": "some.neat.user", "name": "Neat User", "password": "foobar"},
    ]

    # Feature Flag: Email-based Blacklisting
    # Create additional, mocked Users
    test_domains = (
        "blacklisted.com",
        "blacklisted.net",
        "blacklisted.org",
        "notblacklisted.com",
        "mail.blacklisted.com",
    )
    for domain in test_domains:
        mock_email = "foo@" + domain  # e.g. foo@blacklisted.com
        new_user = {
            "username": mock_email,  # Simplifies consistent querying in tests
            "name": domain.replace(".", ""),  # blacklisted.com => blacklistedcom
            "email": mock_email,
            "password": "somepass",
        }
        users.append(new_user)

    groups = [
        {
            "id": "somegroupid",
            "name": "somegroup",
            "description": "Hi there!",
            "members": ["adminuser", "cool.user"],
        },
        {
            "id": "admintenant",
            "name": "somegroup",
            "description": "Hi there!",
            "members": ["adminuser", "cool.user"],
        },
    ]

    def _get_user(username):
        for user in users:
            if user["username"] == username:
                user_data = {}
                user_data["id"] = username
                user_data["name"] = username
                if requires_email:
                    user_data["email"] = user.get("email") or username + "@example.com"
                return user_data

        return None

    ks_app = Flask("testks")
    ks_app.config["SERVER_HOSTNAME"] = "localhost:%s" % _PORT_NUMBER
    if os.environ.get("DEBUG") == "true":
        ks_app.config["DEBUG"] = True

    @ks_app.route("/v2.0/admin/users/<userid>", methods=["GET"])
    def getuser(userid):
        for user in users:
            if user["username"] == userid:
                user_data = {}
                user_data["name"] = userid
                if requires_email:
                    user_data["email"] = user.get("email") or userid + "@example.com"
                return json.dumps({"user": user_data})

        abort(404)

    # v2 referred to all groups as tenants, so replace occurrences of 'group' with 'tenant'
    @ks_app.route("/v2.0/admin/tenants/<tenant>/users", methods=["GET"])
    def getv2_tenant_members(tenant):
        return getv3groupmembers(tenant)

    @ks_app.route("/v3/identity/groups/<groupid>/users", methods=["GET"])
    def getv3groupmembers(groupid):
        for group in groups:
            if group["id"] == groupid:
                group_data = {
                    "links": {},
                    "users": [_get_user(username) for username in group["members"]],
                }

                return json.dumps(group_data)

        abort(404)

    @ks_app.route("/v3/identity/groups/<groupid>", methods=["GET"])
    def getv3group(groupid):
        for group in groups:
            if group["id"] == groupid:
                group_data = {
                    "description": group["description"],
                    "domain_id": "default",
                    "id": groupid,
                    "links": {},
                    "name": group["name"],
                }

                return json.dumps({"group": group_data})

        abort(404)

    @ks_app.route("/v3/identity/users/<userid>", methods=["GET"])
    def getv3user(userid):
        for user in users:
            if user["username"] == userid:
                user_data = {
                    "domain_id": "default",
                    "enabled": True,
                    "id": user["username"],
                    "links": {},
                    "name": user["username"],
                }

                if requires_email:
                    user_data["email"] = user.get("email") or user["username"] + "@example.com"

                return json.dumps({"user": user_data})

        abort(404)

    @ks_app.route("/v3/identity/users", methods=["GET"])
    def v3identity():
        returned = []
        for user in users:
            if not request.args.get("name") or user["username"].startswith(
                request.args.get("name")
            ):
                returned.append(
                    {
                        "domain_id": "default",
                        "enabled": True,
                        "id": user["username"],
                        "links": {},
                        "name": user["username"],
                        "email": user.get("email") or user["username"] + "@example.com",
                    }
                )

        return json.dumps({"users": returned})

    @ks_app.route("/v3/auth/tokens", methods=["POST"])
    def v3tokens():
        creds = request.json["auth"]["identity"]["password"]["user"]
        for user in users:
            if creds["name"] == user["username"] and creds["password"] == user["password"]:
                data = json.dumps(
                    {
                        "token": {
                            "methods": ["password"],
                            "roles": [
                                {"id": "9fe2ff9ee4384b1894a90878d3e92bab", "name": "_member_"},
                                {"id": "c703057be878458588961ce9a0ce686b", "name": "admin"},
                            ],
                            "project": {
                                "domain": {"id": "default", "name": "Default"},
                                "id": "8538a3f13f9541b28c2620eb19065e45",
                                "name": "admin",
                            },
                            "catalog": [
                                {
                                    "endpoints": [
                                        {
                                            "url": server_url + "/v3/identity",
                                            "region": "RegionOne",
                                            "interface": "admin",
                                            "id": "29beb2f1567642eb810b042b6719ea88",
                                        },
                                    ],
                                    "type": "identity",
                                    "id": "bd73972c0e14fb69bae8ff76e112a90",
                                    "name": "keystone",
                                }
                            ],
                            "extras": {},
                            "user": {
                                "domain": {"id": "default", "name": "Default"},
                                "id": user["username"],
                                "name": "admin",
                            },
                            "audit_ids": ["yRt0UrxJSs6-WYJgwEMMmg"],
                            "issued_at": "2014-06-16T22:24:26.089380",
                            "expires_at": "2020-06-16T23:24:26Z",
                        }
                    }
                )

                response = make_response(data, 200)
                response.headers["X-Subject-Token"] = "sometoken"
                return response

        abort(403)

    @ks_app.route("/v2.0/auth/tokens", methods=["POST"])
    def tokens():
        creds = request.json["auth"]["passwordCredentials"]
        for user in users:
            if creds["username"] == user["username"] and creds["password"] == user["password"]:
                return json.dumps(
                    {
                        "access": {
                            "token": {
                                "issued_at": "2014-06-16T22:24:26.089380",
                                "expires": "2020-06-16T23:24:26Z",
                                "id": creds["username"],
                                "tenant": {"id": "sometenant"},
                            },
                            "serviceCatalog": [
                                {
                                    "endpoints": [
                                        {
                                            "adminURL": server_url + "/v2.0/admin",
                                        }
                                    ],
                                    "endpoints_links": [],
                                    "type": "identity",
                                    "name": "admin",
                                },
                            ],
                            "user": {
                                "username": creds["username"],
                                "roles_links": [],
                                "id": creds["username"],
                                "roles": [],
                                "name": user["name"],
                            },
                            "metadata": {
                                "is_admin": 0,
                                "roles": [],
                            },
                        },
                    }
                )

        abort(403)

    return ks_app, _PORT_NUMBER


class KeystoneAuthTestsMixin:
    maxDiff = None

    @property
    def emails(self):
        raise NotImplementedError

    def fake_keystone(self):
        raise NotImplementedError

    def setUp(self):
        setup_database_for_testing(self)
        self.session = requests.Session()

    def tearDown(self):
        finished_database_for_testing(self)

    def test_invalid_user(self):
        with self.fake_keystone() as keystone:
            (user, _) = keystone.verify_credentials("unknownuser", "password")
            self.assertIsNone(user)

    def test_invalid_password(self):
        with self.fake_keystone() as keystone:
            (user, _) = keystone.verify_credentials("cool.user", "notpassword")
            self.assertIsNone(user)

    def test_cooluser(self):
        with self.fake_keystone() as keystone:
            (user, _) = keystone.verify_credentials("cool.user", "password")
            self.assertEqual(user.username, "cool.user")
            self.assertEqual(user.email, "cool.user@example.com" if self.emails else None)

    def test_neatuser(self):
        with self.fake_keystone() as keystone:
            (user, _) = keystone.verify_credentials("some.neat.user", "foobar")
            self.assertEqual(user.username, "some.neat.user")
            self.assertEqual(user.email, "some.neat.user@example.com" if self.emails else None)


class KeystoneV2AuthNoEmailTests(KeystoneAuthTestsMixin, unittest.TestCase):
    def fake_keystone(self):
        return fake_keystone(2, requires_email=False)

    @property
    def emails(self):
        return False


class KeystoneV3AuthNoEmailTests(KeystoneAuthTestsMixin, unittest.TestCase):
    def fake_keystone(self):
        return fake_keystone(3, requires_email=False)

    @property
    def emails(self):
        return False


class KeystoneV2AuthTests(KeystoneAuthTestsMixin, unittest.TestCase):
    def fake_keystone(self):
        return fake_keystone(2, requires_email=True)

    @property
    def emails(self):
        return True


class KeystoneV3AuthTests(KeystoneAuthTestsMixin, unittest.TestCase):
    def fake_keystone(self):
        return fake_keystone(3, requires_email=True)

    def emails(self):
        return True

    def test_query(self):
        with self.fake_keystone() as keystone:
            # Lookup cool.
            (response, federated_id, error_message) = keystone.query_users("cool")
            self.assertIsNone(error_message)
            self.assertEqual(1, len(response))
            self.assertEqual("keystone", federated_id)

            user_info = response[0]
            self.assertEqual("cool.user", user_info.username)

            # Lookup unknown.
            (response, federated_id, error_message) = keystone.query_users("unknown")
            self.assertIsNone(error_message)
            self.assertEqual(0, len(response))
            self.assertEqual("keystone", federated_id)

    def test_link_user(self):
        with self.fake_keystone() as keystone:
            # Link someuser.
            user, error_message = keystone.link_user("cool.user")
            self.assertIsNone(error_message)
            self.assertIsNotNone(user)
            self.assertEqual("cool_user", user.username)
            self.assertEqual("cool.user@example.com", user.email)

            # Link again. Should return the same user record.
            user_again, _ = keystone.link_user("cool.user")
            self.assertEqual(user_again.id, user.id)

            # Confirm someuser.
            result, _ = keystone.confirm_existing_user("cool_user", "password")
            self.assertIsNotNone(result)
            self.assertEqual("cool_user", result.username)

    def test_check_group_lookup_args(self):
        with self.fake_keystone() as keystone:
            (status, err) = keystone.check_group_lookup_args({})
            self.assertFalse(status)
            self.assertEqual("Missing group_id", err)

            (status, err) = keystone.check_group_lookup_args({"group_id": "unknownid"})
            self.assertFalse(status)
            self.assertEqual("Group not found", err)

            (status, err) = keystone.check_group_lookup_args({"group_id": "somegroupid"})
            self.assertTrue(status)
            self.assertIsNone(err)

    def test_iterate_group_members(self):
        with self.fake_keystone() as keystone:
            (itt, err) = keystone.iterate_group_members({"group_id": "somegroupid"})
            self.assertIsNone(err)

            results = list(itt)
            results.sort()

            self.assertEqual(2, len(results))
            self.assertEqual("adminuser", results[0][0].id)
            self.assertEqual("cool.user", results[1][0].id)


if __name__ == "__main__":
    unittest.main()
