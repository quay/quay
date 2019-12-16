import unittest
import mock

from data.database import User
from data import model

from config_app.config_endpoints.api.suconfig import (
    SuperUserConfig,
    SuperUserConfigValidate,
    SuperUserConfigFile,
    SuperUserRegistryStatus,
    SuperUserCreateInitialSuperUser,
)
from config_app.config_endpoints.api import api_bp
from config_app.config_test import ApiTestCase, READ_ACCESS_USER, ADMIN_ACCESS_USER
from config_app.c_app import app, config_provider

try:
    app.register_blueprint(api_bp, url_prefix="/api")
except ValueError:
    # This blueprint was already registered
    pass

# OVERRIDES FROM PORTING FROM OLD APP:
all_queues = []  # the config app doesn't have any queues


class FreshConfigProvider(object):
    def __enter__(self):
        config_provider.reset_for_test()
        return config_provider

    def __exit__(self, type, value, traceback):
        config_provider.reset_for_test()


class TestSuperUserRegistryStatus(ApiTestCase):
    def test_registry_status_no_config(self):
        with FreshConfigProvider():
            json = self.getJsonResponse(SuperUserRegistryStatus)
            self.assertEqual("config-db", json["status"])

    @mock.patch(
        "config_app.config_endpoints.api.suconfig.database_is_valid", mock.Mock(return_value=False)
    )
    def test_registry_status_no_database(self):
        with FreshConfigProvider():
            config_provider.save_config({"key": "value"})
            json = self.getJsonResponse(SuperUserRegistryStatus)
            self.assertEqual("setup-db", json["status"])

    @mock.patch(
        "config_app.config_endpoints.api.suconfig.database_is_valid", mock.Mock(return_value=True)
    )
    def test_registry_status_db_has_superuser(self):
        with FreshConfigProvider():
            config_provider.save_config({"key": "value"})
            json = self.getJsonResponse(SuperUserRegistryStatus)
            self.assertEqual("config", json["status"])

    @mock.patch(
        "config_app.config_endpoints.api.suconfig.database_is_valid", mock.Mock(return_value=True)
    )
    @mock.patch(
        "config_app.config_endpoints.api.suconfig.database_has_users", mock.Mock(return_value=False)
    )
    def test_registry_status_db_no_superuser(self):
        with FreshConfigProvider():
            config_provider.save_config({"key": "value"})
            json = self.getJsonResponse(SuperUserRegistryStatus)
            self.assertEqual("create-superuser", json["status"])

    @mock.patch(
        "config_app.config_endpoints.api.suconfig.database_is_valid", mock.Mock(return_value=True)
    )
    @mock.patch(
        "config_app.config_endpoints.api.suconfig.database_has_users", mock.Mock(return_value=True)
    )
    def test_registry_status_setup_complete(self):
        with FreshConfigProvider():
            config_provider.save_config({"key": "value", "SETUP_COMPLETE": True})
            json = self.getJsonResponse(SuperUserRegistryStatus)
            self.assertEqual("config", json["status"])


class TestSuperUserConfigFile(ApiTestCase):
    def test_get_superuser_invalid_filename(self):
        with FreshConfigProvider():
            self.getResponse(
                SuperUserConfigFile, params=dict(filename="somefile"), expected_code=404
            )

    def test_get_superuser(self):
        with FreshConfigProvider():
            result = self.getJsonResponse(SuperUserConfigFile, params=dict(filename="ssl.cert"))
            self.assertFalse(result["exists"])

    def test_post_no_file(self):
        with FreshConfigProvider():
            # No file
            self.postResponse(
                SuperUserConfigFile, params=dict(filename="ssl.cert"), expected_code=400
            )

    def test_post_superuser_invalid_filename(self):
        with FreshConfigProvider():
            self.postResponse(
                SuperUserConfigFile, params=dict(filename="somefile"), expected_code=404
            )

    def test_post_superuser(self):
        with FreshConfigProvider():
            self.postResponse(
                SuperUserConfigFile, params=dict(filename="ssl.cert"), expected_code=400
            )


class TestSuperUserCreateInitialSuperUser(ApiTestCase):
    def test_no_config_file(self):
        with FreshConfigProvider():
            # If there is no config.yaml, then this method should security fail.
            data = dict(username="cooluser", password="password", email="fake@example.com")
            self.postResponse(SuperUserCreateInitialSuperUser, data=data, expected_code=403)

    def test_config_file_with_db_users(self):
        with FreshConfigProvider():
            # Write some config.
            self.putJsonResponse(SuperUserConfig, data=dict(config={}, hostname="foobar"))

            # If there is a config.yaml, but existing DB users exist, then this method should security
            # fail.
            data = dict(username="cooluser", password="password", email="fake@example.com")
            self.postResponse(SuperUserCreateInitialSuperUser, data=data, expected_code=403)

    def test_config_file_with_no_db_users(self):
        with FreshConfigProvider():
            # Write some config.
            self.putJsonResponse(SuperUserConfig, data=dict(config={}, hostname="foobar"))

            # Delete all the users in the DB.
            for user in list(User.select()):
                model.user.delete_user(user, all_queues)

            # This method should now succeed.
            data = dict(username="cooluser", password="password", email="fake@example.com")
            result = self.postJsonResponse(SuperUserCreateInitialSuperUser, data=data)
            self.assertTrue(result["status"])

            # Verify the superuser was created.
            User.get(User.username == "cooluser")

            # Verify the superuser was placed into the config.
            result = self.getJsonResponse(SuperUserConfig)
            self.assertEqual(["cooluser"], result["config"]["SUPER_USERS"])


class TestSuperUserConfigValidate(ApiTestCase):
    def test_nonsuperuser_noconfig(self):
        with FreshConfigProvider():
            result = self.postJsonResponse(
                SuperUserConfigValidate, params=dict(service="someservice"), data=dict(config={})
            )

            self.assertFalse(result["status"])

    def test_nonsuperuser_config(self):
        with FreshConfigProvider():
            # The validate config call works if there is no config.yaml OR the user is a superuser.
            # Add a config, and verify it breaks when unauthenticated.
            json = self.putJsonResponse(SuperUserConfig, data=dict(config={}, hostname="foobar"))
            self.assertTrue(json["exists"])

            result = self.postJsonResponse(
                SuperUserConfigValidate, params=dict(service="someservice"), data=dict(config={})
            )

            self.assertFalse(result["status"])


class TestSuperUserConfig(ApiTestCase):
    def test_get_superuser(self):
        with FreshConfigProvider():
            json = self.getJsonResponse(SuperUserConfig)

            # Note: We expect the config to be none because a config.yaml should never be checked into
            # the directory.
            self.assertIsNone(json["config"])

    def test_put(self):
        with FreshConfigProvider() as config:
            json = self.putJsonResponse(SuperUserConfig, data=dict(config={}, hostname="foobar"))
            self.assertTrue(json["exists"])

            # Verify the config file exists.
            self.assertTrue(config.config_exists())

            # This should succeed.
            json = self.putJsonResponse(SuperUserConfig, data=dict(config={}, hostname="barbaz"))
            self.assertTrue(json["exists"])

            json = self.getJsonResponse(SuperUserConfig)
            self.assertIsNotNone(json["config"])


if __name__ == "__main__":
    unittest.main()
