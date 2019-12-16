from io import StringIO
from mockldap import MockLdap

from data import database, model
from util.security.test.test_ssl_util import generate_test_cert

from config_app.c_app import app
from config_app.config_test import ApiTestCase, all_queues, ADMIN_ACCESS_USER, ADMIN_ACCESS_EMAIL
from config_app.config_endpoints.api import api_bp
from config_app.config_endpoints.api.superuser import (
    SuperUserCustomCertificate,
    SuperUserCustomCertificates,
)
from config_app.config_endpoints.api.suconfig import (
    SuperUserConfig,
    SuperUserCreateInitialSuperUser,
    SuperUserConfigFile,
    SuperUserRegistryStatus,
)

try:
    app.register_blueprint(api_bp, url_prefix="/api")
except ValueError:
    # This blueprint was already registered
    pass


class TestSuperUserCreateInitialSuperUser(ApiTestCase):
    def test_create_superuser(self):
        data = {
            "username": "newsuper",
            "password": "password",
            "email": "jschorr+fake@devtable.com",
        }

        # Add some fake config.
        fake_config = {
            "AUTHENTICATION_TYPE": "Database",
            "SECRET_KEY": "fakekey",
        }

        self.putJsonResponse(SuperUserConfig, data=dict(config=fake_config, hostname="fakehost"))

        # Try to write with config. Should 403 since there are users in the DB.
        self.postResponse(SuperUserCreateInitialSuperUser, data=data, expected_code=403)

        # Delete all users in the DB.
        for user in list(database.User.select()):
            model.user.delete_user(user, all_queues)

        # Create the superuser.
        self.postJsonResponse(SuperUserCreateInitialSuperUser, data=data)

        # Ensure the user exists in the DB.
        self.assertIsNotNone(model.user.get_user("newsuper"))

        # Ensure that the current user is a superuser in the config.
        json = self.getJsonResponse(SuperUserConfig)
        self.assertEqual(["newsuper"], json["config"]["SUPER_USERS"])

        # Ensure that the current user is a superuser in memory by trying to call an API
        # that will fail otherwise.
        self.getResponse(SuperUserConfigFile, params=dict(filename="ssl.cert"))


class TestSuperUserConfig(ApiTestCase):
    def test_get_status_update_config(self):
        # With no config the status should be 'config-db'.
        json = self.getJsonResponse(SuperUserRegistryStatus)
        self.assertEqual("config-db", json["status"])

        # Add some fake config.
        fake_config = {
            "AUTHENTICATION_TYPE": "Database",
            "SECRET_KEY": "fakekey",
        }

        json = self.putJsonResponse(
            SuperUserConfig, data=dict(config=fake_config, hostname="fakehost")
        )
        self.assertEqual("fakekey", json["config"]["SECRET_KEY"])
        self.assertEqual("fakehost", json["config"]["SERVER_HOSTNAME"])
        self.assertEqual("Database", json["config"]["AUTHENTICATION_TYPE"])

        # With config the status should be 'setup-db'.
        # TODO: fix this test
        # json = self.getJsonResponse(SuperUserRegistryStatus)
        # self.assertEquals('setup-db', json['status'])

    def test_config_file(self):
        # Try for an invalid file. Should 404.
        self.getResponse(SuperUserConfigFile, params=dict(filename="foobar"), expected_code=404)

        # Try for a valid filename. Should not exist.
        json = self.getJsonResponse(SuperUserConfigFile, params=dict(filename="ssl.cert"))
        self.assertFalse(json["exists"])

        # Add the file.
        self.postResponse(
            SuperUserConfigFile,
            params=dict(filename="ssl.cert"),
            file=(StringIO("my file contents"), "ssl.cert"),
        )

        # Should now exist.
        json = self.getJsonResponse(SuperUserConfigFile, params=dict(filename="ssl.cert"))
        self.assertTrue(json["exists"])

    def test_update_with_external_auth(self):
        # Run a mock LDAP.
        mockldap = MockLdap(
            {
                "dc=quay,dc=io": {"dc": ["quay", "io"]},
                "ou=employees,dc=quay,dc=io": {"dc": ["quay", "io"], "ou": "employees"},
                "uid="
                + ADMIN_ACCESS_USER
                + ",ou=employees,dc=quay,dc=io": {
                    "dc": ["quay", "io"],
                    "ou": "employees",
                    "uid": [ADMIN_ACCESS_USER],
                    "userPassword": ["password"],
                    "mail": [ADMIN_ACCESS_EMAIL],
                },
            }
        )

        config = {
            "AUTHENTICATION_TYPE": "LDAP",
            "LDAP_BASE_DN": ["dc=quay", "dc=io"],
            "LDAP_ADMIN_DN": "uid=devtable,ou=employees,dc=quay,dc=io",
            "LDAP_ADMIN_PASSWD": "password",
            "LDAP_USER_RDN": ["ou=employees"],
            "LDAP_UID_ATTR": "uid",
            "LDAP_EMAIL_ATTR": "mail",
        }

        mockldap.start()
        try:
            # Write the config with the valid password.
            self.putResponse(
                SuperUserConfig,
                data={"config": config, "password": "password", "hostname": "foo"},
                expected_code=200,
            )

            # Ensure that the user row has been linked.
            # TODO: fix this test
            # self.assertEquals(ADMIN_ACCESS_USER,
            #                   model.user.verify_federated_login('ldap', ADMIN_ACCESS_USER).username)
        finally:
            mockldap.stop()


class TestSuperUserCustomCertificates(ApiTestCase):
    def test_custom_certificates(self):

        # Upload a certificate.
        cert_contents, _ = generate_test_cert(
            hostname="somecoolhost", san_list=["DNS:bar", "DNS:baz"]
        )
        self.postResponse(
            SuperUserCustomCertificate,
            params=dict(certpath="testcert.crt"),
            file=(StringIO(cert_contents), "testcert.crt"),
            expected_code=204,
        )

        # Make sure it is present.
        json = self.getJsonResponse(SuperUserCustomCertificates)
        self.assertEqual(1, len(json["certs"]))

        cert_info = json["certs"][0]
        self.assertEqual("testcert.crt", cert_info["path"])

        self.assertEqual(set(["somecoolhost", "bar", "baz"]), set(cert_info["names"]))
        self.assertFalse(cert_info["expired"])

        # Remove the certificate.
        self.deleteResponse(SuperUserCustomCertificate, params=dict(certpath="testcert.crt"))

        # Make sure it is gone.
        json = self.getJsonResponse(SuperUserCustomCertificates)
        self.assertEqual(0, len(json["certs"]))

    def test_expired_custom_certificate(self):
        # Upload a certificate.
        cert_contents, _ = generate_test_cert(hostname="somecoolhost", expires=-10)
        self.postResponse(
            SuperUserCustomCertificate,
            params=dict(certpath="testcert.crt"),
            file=(StringIO(cert_contents), "testcert.crt"),
            expected_code=204,
        )

        # Make sure it is present.
        json = self.getJsonResponse(SuperUserCustomCertificates)
        self.assertEqual(1, len(json["certs"]))

        cert_info = json["certs"][0]
        self.assertEqual("testcert.crt", cert_info["path"])

        self.assertEqual(set(["somecoolhost"]), set(cert_info["names"]))
        self.assertTrue(cert_info["expired"])

    def test_invalid_custom_certificate(self):
        # Upload an invalid certificate.
        self.postResponse(
            SuperUserCustomCertificate,
            params=dict(certpath="testcert.crt"),
            file=(StringIO("some contents"), "testcert.crt"),
            expected_code=204,
        )

        # Make sure it is present but invalid.
        json = self.getJsonResponse(SuperUserCustomCertificates)
        self.assertEqual(1, len(json["certs"]))

        cert_info = json["certs"][0]
        self.assertEqual("testcert.crt", cert_info["path"])
        self.assertEqual("no start line", cert_info["error"])

    def test_path_sanitization(self):
        # Upload a certificate.
        cert_contents, _ = generate_test_cert(hostname="somecoolhost", expires=-10)
        self.postResponse(
            SuperUserCustomCertificate,
            params=dict(certpath="testcert/../foobar.crt"),
            file=(StringIO(cert_contents), "testcert/../foobar.crt"),
            expected_code=204,
        )

        # Make sure it is present.
        json = self.getJsonResponse(SuperUserCustomCertificates)
        self.assertEqual(1, len(json["certs"]))

        cert_info = json["certs"][0]
        self.assertEqual("foobar.crt", cert_info["path"])
