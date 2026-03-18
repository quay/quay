import os
import tempfile
from contextlib import contextmanager

import jinja2
import pytest
from six import iteritems
from supervisor.options import ServerOptions

from ..supervisord_conf_create import (
    _FEDERATED_AUTH_TYPES,
    QUAY_OVERRIDE_SERVICES,
    QUAY_SERVICES,
    WORKER_FEATURE_GATES,
    _apply_feature_gates,
    _load_quay_config,
    limit_services,
    override_services,
    registry_services,
)


@contextmanager
def environ(**kwargs):
    original_env = {key: os.getenv(key) for key in kwargs}
    os.environ.update(**kwargs)
    try:
        yield
    finally:
        for key, value in iteritems(original_env):
            if value is None:
                del os.environ[key]
            else:
                os.environ[key] = value


def render_supervisord_conf(config):
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../supervisord.conf.jnj")
    ) as f:
        template = jinja2.Template(f.read())
    return template.render(config=config)


def test_supervisord_conf_create_registry():
    config = registry_services()
    limit_services(config, [])
    rendered_config_file = render_supervisord_conf(config)

    with environ(
        QUAYPATH=".", QUAYDIR="/", QUAYCONF="/conf", DB_CONNECTION_POOLING_REGISTRY="true"
    ):
        opts = ServerOptions()

        with tempfile.NamedTemporaryFile(mode="w") as f:
            f.write(rendered_config_file)
            f.flush()

            opts.searchpaths = [f.name]
            assert opts.default_configfile() == f.name


# ---------------------------------------------------------------------------
# Feature-gate tests
# ---------------------------------------------------------------------------

INFRASTRUCTURE_SERVICES = {
    "dnsmasq",
    "gunicorn-registry",
    "gunicorn-web",
    "ip-resolver-update-worker",
    "memcache",
    "nginx",
    "pushgateway",
    "servicekey",
}


class TestApplyFeatureGates:
    """Tests for _apply_feature_gates()."""

    def test_none_config_is_noop(self):
        services = registry_services()
        original = {k: dict(v) for k, v in services.items()}
        _apply_feature_gates(services, None)
        assert services == original

    def test_account_recovery_mode_disables_all_gated_workers(self):
        services = registry_services()
        quay_config = {"ACCOUNT_RECOVERY_MODE": True}
        _apply_feature_gates(services, quay_config)

        for service in WORKER_FEATURE_GATES:
            if service in services:
                assert (
                    services[service]["autostart"] == "false"
                ), f"{service} should be disabled in ACCOUNT_RECOVERY_MODE"

    def test_account_recovery_mode_leaves_infrastructure_alone(self):
        services = registry_services()
        quay_config = {"ACCOUNT_RECOVERY_MODE": True}
        _apply_feature_gates(services, quay_config)

        for service in INFRASTRUCTURE_SERVICES:
            if service in services:
                assert (
                    services[service]["autostart"] == "true"
                ), f"{service} should remain enabled in ACCOUNT_RECOVERY_MODE"

    def test_features_off_disables_workers(self):
        services = registry_services()
        quay_config = {
            "FEATURE_SECURITY_SCANNER": False,
            "FEATURE_REPO_MIRROR": False,
            "FEATURE_AUTO_PRUNE": False,
        }
        _apply_feature_gates(services, quay_config)

        assert services["securityworker"]["autostart"] == "false"
        assert services["gunicorn-secscan"]["autostart"] == "false"
        assert services["repomirrorworker"]["autostart"] == "false"
        assert services["autopruneworker"]["autostart"] == "false"

    def test_features_on_keeps_workers_enabled(self):
        """When features are on, feature gates should NOT disable workers.

        Note: repomirrorworker starts with autostart=false in registry_services()
        so it remains false -- feature gates only disable, never enable.
        """
        services = registry_services()
        original = {k: dict(v) for k, v in services.items()}
        quay_config = {
            "FEATURE_SECURITY_SCANNER": True,
            "FEATURE_SECURITY_NOTIFICATIONS": True,
            "FEATURE_REPO_MIRROR": True,
            "FEATURE_AUTO_PRUNE": True,
            "FEATURE_QUOTA_MANAGEMENT": True,
        }
        _apply_feature_gates(services, quay_config)

        # Workers whose initial autostart is "true" should remain "true"
        assert services["securityworker"]["autostart"] == "true"
        assert services["gunicorn-secscan"]["autostart"] == "true"
        assert services["securityscanningnotificationworker"]["autostart"] == "true"
        assert services["autopruneworker"]["autostart"] == "true"
        assert services["quotatotalworker"]["autostart"] == "true"
        assert services["quotaregistrysizeworker"]["autostart"] == "true"

        # repomirrorworker starts as "false" in registry_services(); gate doesn't enable it
        assert (
            services["repomirrorworker"]["autostart"] == original["repomirrorworker"]["autostart"]
        )

    def test_secscan_notification_requires_both_flags(self):
        services = registry_services()
        quay_config = {
            "FEATURE_SECURITY_SCANNER": True,
            "FEATURE_SECURITY_NOTIFICATIONS": False,
        }
        _apply_feature_gates(services, quay_config)
        assert services["securityscanningnotificationworker"]["autostart"] == "false"

        services = registry_services()
        quay_config = {
            "FEATURE_SECURITY_SCANNER": False,
            "FEATURE_SECURITY_NOTIFICATIONS": True,
        }
        _apply_feature_gates(services, quay_config)
        assert services["securityscanningnotificationworker"]["autostart"] == "false"

    def test_infrastructure_services_never_affected(self):
        services = registry_services()
        quay_config = {
            "FEATURE_SECURITY_SCANNER": False,
            "FEATURE_BUILD_SUPPORT": False,
            "FEATURE_GARBAGE_COLLECTION": False,
        }
        _apply_feature_gates(services, quay_config)

        for service in INFRASTRUCTURE_SERVICES:
            if service in services:
                assert (
                    services[service]["autostart"] == "true"
                ), f"Infrastructure service {service} should never be disabled by feature gates"

    def test_expired_app_token_requires_both_feature_and_config(self):
        services = registry_services()
        quay_config = {
            "FEATURE_APP_SPECIFIC_TOKENS": True,
            # No EXPIRED_APP_SPECIFIC_TOKEN_GC key
        }
        _apply_feature_gates(services, quay_config)
        assert services["expiredappspecifictokenworker"]["autostart"] == "false"

        services = registry_services()
        quay_config = {
            "FEATURE_APP_SPECIFIC_TOKENS": True,
            "EXPIRED_APP_SPECIFIC_TOKEN_GC": "1d",
        }
        _apply_feature_gates(services, quay_config)
        assert services["expiredappspecifictokenworker"]["autostart"] == "true"

    def test_logrotateworker_requires_feature_and_paths(self):
        services = registry_services()
        quay_config = {
            "FEATURE_ACTION_LOG_ROTATION": True,
            # Missing paths
        }
        _apply_feature_gates(services, quay_config)
        assert services["logrotateworker"]["autostart"] == "false"

        services = registry_services()
        quay_config = {
            "FEATURE_ACTION_LOG_ROTATION": True,
            "ACTION_LOG_ARCHIVE_PATH": "/path",
            "ACTION_LOG_ARCHIVE_LOCATION": "s3",
        }
        _apply_feature_gates(services, quay_config)
        assert services["logrotateworker"]["autostart"] == "true"

    def test_pullstatsredis_requires_feature_and_redis_config(self):
        services = registry_services()
        quay_config = {
            "FEATURE_IMAGE_PULL_STATS": True,
            # No PULL_METRICS_REDIS key
        }
        _apply_feature_gates(services, quay_config)
        assert services["pullstatsredisflushworker"]["autostart"] == "false"

        services = registry_services()
        quay_config = {
            "FEATURE_IMAGE_PULL_STATS": True,
            "PULL_METRICS_REDIS": {"host": "redis"},
        }
        _apply_feature_gates(services, quay_config)
        assert services["pullstatsredisflushworker"]["autostart"] == "true"

    def test_chunkcleanupworker_requires_swift_storage(self):
        services = registry_services()
        quay_config = {
            "DISTRIBUTED_STORAGE_CONFIG": {
                "default": ["S3Storage", {"bucket": "quay"}],
            },
        }
        _apply_feature_gates(services, quay_config)
        assert services["chunkcleanupworker"]["autostart"] == "false"

        services = registry_services()
        quay_config = {
            "DISTRIBUTED_STORAGE_CONFIG": {
                "default": ["SwiftStorage", {"container": "quay"}],
            },
        }
        _apply_feature_gates(services, quay_config)
        assert services["chunkcleanupworker"]["autostart"] == "true"


class TestTeamsyncFeatureGate:
    """Tests for teamsync federated auth type checks."""

    def test_teamsync_disabled_for_database_auth(self):
        services = registry_services()
        quay_config = {
            "FEATURE_TEAM_SYNCING": True,
            "AUTHENTICATION_TYPE": "Database",
        }
        _apply_feature_gates(services, quay_config)
        assert services["teamsyncworker"]["autostart"] == "false"

    def test_teamsync_disabled_for_apptoken_auth(self):
        services = registry_services()
        quay_config = {
            "FEATURE_TEAM_SYNCING": True,
            "AUTHENTICATION_TYPE": "AppToken",
        }
        _apply_feature_gates(services, quay_config)
        assert services["teamsyncworker"]["autostart"] == "false"

    @pytest.mark.parametrize("auth_type", sorted(_FEDERATED_AUTH_TYPES))
    def test_teamsync_enabled_for_federated_auth(self, auth_type):
        services = registry_services()
        quay_config = {
            "FEATURE_TEAM_SYNCING": True,
            "AUTHENTICATION_TYPE": auth_type,
        }
        _apply_feature_gates(services, quay_config)
        assert (
            services["teamsyncworker"]["autostart"] == "true"
        ), f"teamsync should be enabled for auth type {auth_type}"

    def test_teamsync_disabled_when_feature_off(self):
        services = registry_services()
        quay_config = {
            "FEATURE_TEAM_SYNCING": False,
            "AUTHENTICATION_TYPE": "LDAP",
        }
        _apply_feature_gates(services, quay_config)
        assert services["teamsyncworker"]["autostart"] == "false"


class TestFeatureGateDefaults:
    """Verify gate defaults match config.py DefaultConfig values."""

    def test_defaults_match_config(self):
        """Workers with default-True features should stay enabled with empty config."""
        services = registry_services()
        quay_config = {}
        _apply_feature_gates(services, quay_config)

        # Default-True features: workers should remain enabled
        default_true_workers = [
            "builder",
            "gcworker",
            "namespacegcworker",
            "repositorygcworker",
            "exportactionlogsworker",
            "manifestbackfillworker",
            "manifestsubjectbackfillworker",
            "repositoryactioncounter",
        ]
        for worker in default_true_workers:
            assert services[worker]["autostart"] == "true", f"{worker} should be enabled by default"

        # Default-False features: workers should be disabled
        default_false_workers = [
            "securityworker",
            "gunicorn-secscan",
            "repomirrorworker",
            "storagereplication",
            "teamsyncworker",
            "quotatotalworker",
            "quotaregistrysizeworker",
            "autopruneworker",
            "reconciliationworker",
            "proxycacheblobworker",
            "globalpromstats",
            "pullstatsredisflushworker",
            "chunkcleanupworker",
        ]
        for worker in default_false_workers:
            assert (
                services[worker]["autostart"] == "false"
            ), f"{worker} should be disabled by default"


class TestGCDisablePushes:
    """GC workers should be disabled when DISABLE_PUSHES is True."""

    GC_WORKERS = ["gcworker", "namespacegcworker", "repositorygcworker"]

    def test_gc_disabled_when_pushes_disabled(self):
        services = registry_services()
        quay_config = {"DISABLE_PUSHES": True}
        _apply_feature_gates(services, quay_config)
        for worker in self.GC_WORKERS:
            assert (
                services[worker]["autostart"] == "false"
            ), f"{worker} should be disabled when DISABLE_PUSHES is True"

    def test_gc_enabled_when_pushes_not_disabled(self):
        services = registry_services()
        quay_config = {"DISABLE_PUSHES": False}
        _apply_feature_gates(services, quay_config)
        for worker in self.GC_WORKERS:
            assert (
                services[worker]["autostart"] == "true"
            ), f"{worker} should be enabled when DISABLE_PUSHES is False"


class TestQuotaBackfillGate:
    """quotatotalworker requires both FEATURE_QUOTA_MANAGEMENT and QUOTA_BACKFILL."""

    def test_disabled_when_backfill_off(self):
        services = registry_services()
        quay_config = {
            "FEATURE_QUOTA_MANAGEMENT": True,
            "QUOTA_BACKFILL": False,
        }
        _apply_feature_gates(services, quay_config)
        assert services["quotatotalworker"]["autostart"] == "false"

    def test_enabled_when_both_on(self):
        services = registry_services()
        quay_config = {
            "FEATURE_QUOTA_MANAGEMENT": True,
            "QUOTA_BACKFILL": True,
        }
        _apply_feature_gates(services, quay_config)
        assert services["quotatotalworker"]["autostart"] == "true"


class TestGlobalPromstatsGate:
    """globalpromstats requires PROMETHEUS_PUSHGATEWAY_URL."""

    def test_disabled_when_url_absent(self):
        services = registry_services()
        quay_config = {}
        _apply_feature_gates(services, quay_config)
        assert services["globalpromstats"]["autostart"] == "false"

    def test_enabled_when_url_present(self):
        services = registry_services()
        quay_config = {"PROMETHEUS_PUSHGATEWAY_URL": "http://pushgateway:9091"}
        _apply_feature_gates(services, quay_config)
        assert services["globalpromstats"]["autostart"] == "true"


class TestProxyCacheBlobDownloadGate:
    """proxycacheblobworker requires FEATURE_PROXY_CACHE and FEATURE_PROXY_CACHE_BLOB_DOWNLOAD."""

    def test_disabled_when_blob_download_off(self):
        services = registry_services()
        quay_config = {
            "FEATURE_PROXY_CACHE": True,
            "FEATURE_PROXY_CACHE_BLOB_DOWNLOAD": False,
        }
        _apply_feature_gates(services, quay_config)
        assert services["proxycacheblobworker"]["autostart"] == "false"

    def test_enabled_when_both_on(self):
        services = registry_services()
        quay_config = {
            "FEATURE_PROXY_CACHE": True,
            "FEATURE_PROXY_CACHE_BLOB_DOWNLOAD": True,
        }
        _apply_feature_gates(services, quay_config)
        assert services["proxycacheblobworker"]["autostart"] == "true"


class TestOverrideOrdering:
    """limit_services / override_services can re-enable feature-gated workers."""

    def test_limit_services_can_reenable(self):
        services = registry_services()
        quay_config = {"FEATURE_SECURITY_SCANNER": False}
        _apply_feature_gates(services, quay_config)
        assert services["securityworker"]["autostart"] == "false"

        # Simulate QUAY_SERVICES=securityworker
        limit_services(services, "securityworker")
        assert services["securityworker"]["autostart"] == "true"

    def test_override_services_can_reenable(self):
        services = registry_services()
        quay_config = {"FEATURE_AUTO_PRUNE": False}
        _apply_feature_gates(services, quay_config)
        assert services["autopruneworker"]["autostart"] == "false"

        # Simulate QUAY_OVERRIDE_SERVICES=autopruneworker=true
        override_services(services, "autopruneworker=true")
        assert services["autopruneworker"]["autostart"] == "true"


class TestLoadQuayConfig:
    """Tests for _load_quay_config()."""

    def test_env_var_overrides(self):
        """QUAY_FEATURE_* env vars should override config values."""
        with environ(QUAY_FEATURE_SECURITY_SCANNER="true"):
            config = _load_quay_config()
            if config is not None:
                assert config.get("FEATURE_SECURITY_SCANNER") is True

    def test_env_var_false_values(self):
        """QUAY_FEATURE_* env vars with false-like values should set False."""
        with environ(QUAY_FEATURE_TEST_FLAG="false"):
            config = _load_quay_config()
            if config is not None:
                assert config.get("FEATURE_TEST_FLAG") is False
