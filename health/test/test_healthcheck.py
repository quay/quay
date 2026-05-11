"""Unit tests for health.healthcheck.HealthCheck and subclasses."""

from unittest.mock import MagicMock, patch

import pytest

from health.healthcheck import HealthCheck, LocalHealthCheck, RDSAwareHealthCheck


def _make_app(health_checker=None):
    app = MagicMock()
    app.config = {
        "TESTING": True,
        "SETUP_COMPLETE": True,
        "HEALTH_CHECKER": health_checker or ("LocalHealthCheck", {}),
        "SERVER_HOSTNAME": "localhost:8080",
        "PREFERRED_URL_SCHEME": "http",
    }
    app.config.get = lambda k, d=None: app.config.get(k, d)
    return app


def _make_app_config(health_checker=None):
    config = {
        "TESTING": True,
        "SETUP_COMPLETE": True,
        "HEALTH_CHECKER": health_checker or ("LocalHealthCheck", {}),
        "SERVER_HOSTNAME": "localhost:8080",
        "PREFERRED_URL_SCHEME": "http",
    }

    app = MagicMock()
    app.config = config
    return app


@pytest.fixture
def mock_deps():
    return MagicMock(), MagicMock()


class TestLocalHealthCheckInstanceSkips:
    def test_default_skips_redis_and_storage(self, mock_deps):
        config_provider, instance_keys = mock_deps
        app = _make_app_config()
        checker = LocalHealthCheck(app, config_provider, instance_keys)
        assert checker.instance_skips == ["redis", "storage"]

    def test_custom_skips_from_constructor(self, mock_deps):
        config_provider, instance_keys = mock_deps
        app = _make_app_config()
        checker = LocalHealthCheck(
            app, config_provider, instance_keys, instance_skips=["redis", "storage", "auth"]
        )
        assert checker.instance_skips == ["redis", "storage", "auth"]

    def test_empty_skips(self, mock_deps):
        config_provider, instance_keys = mock_deps
        app = _make_app_config()
        checker = LocalHealthCheck(app, config_provider, instance_keys, instance_skips=[])
        assert checker.instance_skips == []


class TestRDSAwareHealthCheckInstanceSkips:
    def test_default_skips_redis_and_storage(self, mock_deps):
        config_provider, instance_keys = mock_deps
        app = _make_app_config()
        checker = RDSAwareHealthCheck(app, config_provider, instance_keys)
        assert checker.instance_skips == ["redis", "storage"]

    def test_custom_skips_from_constructor(self, mock_deps):
        config_provider, instance_keys = mock_deps
        app = _make_app_config()
        checker = RDSAwareHealthCheck(
            app, config_provider, instance_keys, instance_skips=["redis", "storage", "database"]
        )
        assert checker.instance_skips == ["redis", "storage", "database"]


class TestGetCheckerForwardsInstanceSkips:
    def test_local_health_check_with_instance_skips(self, mock_deps):
        config_provider, instance_keys = mock_deps
        app = _make_app_config(("LocalHealthCheck", {"instance_skips": ["redis"]}))
        checker = HealthCheck.get_checker(app, config_provider, instance_keys)
        assert isinstance(checker, LocalHealthCheck)
        assert checker.instance_skips == ["redis"]

    def test_local_health_check_without_instance_skips(self, mock_deps):
        config_provider, instance_keys = mock_deps
        app = _make_app_config(("LocalHealthCheck", {}))
        checker = HealthCheck.get_checker(app, config_provider, instance_keys)
        assert isinstance(checker, LocalHealthCheck)
        assert checker.instance_skips == ["redis", "storage"]

    def test_rds_health_check_with_instance_skips(self, mock_deps):
        config_provider, instance_keys = mock_deps
        app = _make_app_config(
            ("RDSAwareHealthCheck", {"instance_skips": ["redis", "storage", "auth"]})
        )
        checker = HealthCheck.get_checker(app, config_provider, instance_keys)
        assert isinstance(checker, RDSAwareHealthCheck)
        assert checker.instance_skips == ["redis", "storage", "auth"]

    def test_production_alias_with_instance_skips(self, mock_deps):
        config_provider, instance_keys = mock_deps
        app = _make_app_config(("ProductionHealthCheck", {"instance_skips": ["redis"]}))
        checker = HealthCheck.get_checker(app, config_provider, instance_keys)
        assert isinstance(checker, RDSAwareHealthCheck)
        assert checker.instance_skips == ["redis"]


class TestCheckInstanceRespectsSkips:
    @patch("health.healthcheck.check_all_services")
    def test_skipped_services_not_checked(self, mock_check_all, mock_deps):
        config_provider, instance_keys = mock_deps
        app = _make_app_config()
        mock_check_all.return_value = {"disk_space": (True, None)}

        checker = LocalHealthCheck(
            app, config_provider, instance_keys, instance_skips=["redis", "storage", "auth"]
        )
        with patch.object(checker, "get_instance_health", return_value=({}, 200)):
            checker.check_instance()

        mock_check_all.assert_called_once_with(app, ["redis", "storage", "auth"], for_instance=True)
