import inspect
import json
import logging
import re

import pytest

from conf.init import service_gating
from conf.init.service_gating import (
    SERVICE_REQUIREMENTS,
    _feature,
    gate_services,
    load_default_config,
    resolve_effective_config,
)
from conf.init.supervisord_conf_create import registry_services

DEFAULTS = load_default_config()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        ("true", True),
        ("True", True),
        ("false", False),
        ("yes", False),
        (None, False),
        ("1", False),
        ("", False),
        ("TRUE", True),
    ],
)
def test_feature_properly_normalizes_enabled_values(value, expected):
    """
    Verifies that _feature properly normalizes true/false values.
    """
    # test configuration
    cfg = {
        "TESTING": value,
    }
    assert _feature(cfg, "TESTING") == expected


def test_feature_does_not_return_true_on_empty_config():
    """
    Verifies that _feature returns False if an empty config is passed.
    """
    config = {}

    assert _feature(config, "TESTING") is False


def _cfg(**overrides):
    """
    Applies overrides to the provided configuration.
    """
    return {**DEFAULTS, **overrides}


@pytest.mark.parametrize(
    ("service", "overrides", "expected"),
    [
        pytest.param(
            "autopruneworker",
            {"FEATURE_AUTO_PRUNE": True},
            True,
            id="autoprune-flag-on",
        ),
        pytest.param(
            "autopruneworker",
            {"FEATURE_AUTO_PRUNE": "false"},
            False,
            id="autoprune-string-false-is-off",
        ),
        pytest.param(
            "teamsyncworker",
            {"FEATURE_TEAM_SYNCING": True, "AUTHENTICATION_TYPE": "LDAP"},
            True,
            id="teamsync-ldap",
        ),
        pytest.param(
            "teamsyncworker",
            {"FEATURE_TEAM_SYNCING": True, "AUTHENTICATION_TYPE": "Database"},
            False,
            id="teamsync-database-unsupported",
        ),
        pytest.param(
            "teamsyncworker",
            {"FEATURE_TEAM_SYNCING": True, "AUTHENTICATION_TYPE": "Keystone"},
            True,
            id="teamsync-keystone",
        ),
        pytest.param(
            "teamsyncworker",
            {"FEATURE_TEAM_SYNCING": True, "AUTHENTICATION_TYPE": "JWT"},
            False,
            id="teamsync-jwt-unsupported",
        ),
        pytest.param(
            "gcworker",
            {"FEATURE_GARBAGE_COLLECTION": True, "DISABLE_PUSHES": True},
            False,
            id="gc-pushes-disabled",
        ),
        pytest.param(
            "gcworker",
            {"FEATURE_GARBAGE_COLLECTION": True, "DISABLE_PUSHES": False},
            True,
            id="gc-pushes-enabled",
        ),
        pytest.param(
            "gcworker",
            {},
            True,
            id="gc-defaults-on",
        ),
        pytest.param(
            "chunkcleanupworker",
            {"DISTRIBUTED_STORAGE_CONFIG": {"swift": ["SwiftStorage", {}]}},
            True,
            id="chunkcleanup-swift-present",
        ),
        pytest.param(
            "chunkcleanupworker",
            {"DISTRIBUTED_STORAGE_CONFIG": {"s3": ["S3Storage", {}]}},
            False,
            id="chunkcleanup-no-swift",
        ),
        pytest.param(
            "builder",
            {"BUILD_MANAGER": ("external", {})},
            False,
            id="builder-external-build-manager",
        ),
        pytest.param(
            "builder",
            {"REGISTRY_STATE": "readonly"},
            False,
            id="builder-readonly-registry",
        ),
        pytest.param(
            "builder",
            {},
            True,
            id="builder-defaults-on",
        ),
        pytest.param(
            "builder",
            {"FEATURE_BUILD_SUPPORT": False},
            False,
            id="builder-build-support-off",
        ),
        pytest.param(
            "builder",
            {"BUILD_MANAGER": None},
            False,
            id="builder-no-build-manager",
        ),
        pytest.param(
            "storagereplication",
            {
                "FEATURE_STORAGE_REPLICATION": True,
                "DISTRIBUTED_STORAGE_CONFIG": {"s3": ["S3Storage", {}]},
            },
            True,
            id="storagereplication-remote-storage",
        ),
        pytest.param(
            "storagereplication",
            {},
            False,
            id="storagereplication-flag-off",
        ),
        pytest.param(
            "storagereplication",
            {
                "FEATURE_STORAGE_REPLICATION": True,
                "DISTRIBUTED_STORAGE_CONFIG": {"local": ["LocalStorage", {}]},
            },
            False,
            id="storagereplication-local-storage-blocks",
        ),
        pytest.param(
            "storagereplication",
            {"FEATURE_STORAGE_REPLICATION": True, "DISTRIBUTED_STORAGE_CONFIG": None},
            True,
            id="storagereplication-no-storage-config",
        ),
        pytest.param(
            "logrotateworker",
            {"FEATURE_ACTION_LOG_ROTATION": True},
            True,
            id="logrotate-archive-path-set",
        ),
        pytest.param(
            "logrotateworker",
            {"FEATURE_ACTION_LOG_ROTATION": True, "ACTION_LOG_ARCHIVE_PATH": None},
            False,
            id="logrotate-archive-path-missing",
        ),
        pytest.param(
            "securityworker",
            {"FEATURE_SECURITY_SCANNER": True},
            True,
            id="securityworker-scanner-on",
        ),
        pytest.param(
            "securityscanningnotificationworker",
            {"FEATURE_SECURITY_SCANNER": True, "FEATURE_SECURITY_NOTIFICATIONS": False},
            False,
            id="secnotification-notifications-off",
        ),
        pytest.param(
            "securityscanningnotificationworker",
            {"FEATURE_SECURITY_SCANNER": True, "FEATURE_SECURITY_NOTIFICATIONS": True},
            True,
            id="secnotification-both-on",
        ),
        pytest.param(
            "securityscanningnotificationworker",
            {"FEATURE_SECURITY_SCANNER": False, "FEATURE_SECURITY_NOTIFICATIONS": True},
            False,
            id="secnotification-scanner-off",
        ),
        pytest.param(
            "gunicorn-secscan",
            {
                "FEATURE_SECURITY_SCANNER": True,
                "FEATURE_SECURITY_NOTIFICATIONS": True,
                "ACCOUNT_RECOVERY_MODE": True,
            },
            False,
            id="secscan-recovery-mode",
        ),
        pytest.param(
            "quotatotalworker",
            {"FEATURE_QUOTA_MANAGEMENT": True},
            True,
            id="quotatotal-backfill-enabled",
        ),
        pytest.param(
            "quotatotalworker",
            {"FEATURE_QUOTA_MANAGEMENT": True, "QUOTA_BACKFILL": False},
            False,
            id="quotatotal-backfill-disabled",
        ),
        pytest.param(
            "pullstatsredisflushworker",
            {"FEATURE_IMAGE_PULL_STATS": True, "TESTING": False},
            True,
            id="pullstats-production-mode",
        ),
        pytest.param(
            "pullstatsredisflushworker",
            {"FEATURE_IMAGE_PULL_STATS": True, "TESTING": True},
            False,
            id="pullstats-testing-mode",
        ),
        pytest.param(
            "pullstatsredisflushworker",
            {"FEATURE_IMAGE_PULL_STATS": True, "TESTING": False, "PULL_METRICS_REDIS": None},
            False,
            id="pullstats-redis-missing",
        ),
    ],
)
def test_rule(service, overrides, expected):
    """
    Verifies that all the override rules are properly applied and that we return proper values for the respective
    worker.
    """
    cfg = _cfg(**overrides)
    assert SERVICE_REQUIREMENTS[service](cfg) is expected


def test_rules_reference_real_services():
    """
    Verifies that every rule names a service that exists in registry_services(). A misspelled name
    would otherwise silently never gate anything.
    """
    assert set(SERVICE_REQUIREMENTS) <= set(registry_services())


def test_rules_are_callable():
    """
    Verifies that every rule is a function, not a bare value.
    """
    assert all(callable(rule) for rule in SERVICE_REQUIREMENTS.values())


def test_config_keys_used_by_rules_exist_in_default_config():
    """
    Verifies that every config key read by service_gating.py exists in DefaultConfig. A misspelled
    key reads as missing and would wrongly turn a service off.
    """
    source = inspect.getsource(service_gating)
    keys = set(re.findall(r'_feature\(\w+,\s*"([A-Z0-9_]+)"', source))
    keys |= set(re.findall(r'\.get\(\s*"([A-Z0-9_]+)"', source))

    assert keys, "no config keys found, the pattern is probably out of date"
    assert keys - set(DEFAULTS) == set()


def test_gate_services_turns_off_services_whose_rule_is_false():
    config = registry_services()
    effective = _cfg(FEATURE_AUTO_PRUNE=True)

    disabled = gate_services(config, effective)

    assert config["autopruneworker"]["autostart"] == "true"
    assert "autopruneworker" not in disabled
    assert config["securityworker"]["autostart"] == "false"
    assert "securityworker" in disabled


def test_gate_services_never_turns_a_service_on():
    """
    Verifies that services which start disabled (repomirrorworker) are left as they are.
    """
    config = registry_services()

    gate_services(config, _cfg(FEATURE_REPO_MIRROR=True))

    assert config["repomirrorworker"]["autostart"] == "false"


@pytest.mark.parametrize(
    "service",
    ["nginx", "gunicorn-web", "gunicorn-registry", "globalpromstats", "servicekey", "memcache"],
)
def test_gate_services_leaves_ungated_services_alone(service):
    """
    Verifies that services that are detrimental to the registry always start.
    """
    config = registry_services()

    gate_services(config, _cfg())

    assert config[service]["autostart"] == "true"


def test_gate_services_does_nothing_without_effective_config():
    """
    Verifies the fail-open path: with no trustworthy config, every service keeps its default.
    """
    config = registry_services()

    assert gate_services(config, None) == []
    assert config == registry_services()


def test_gate_services_ignores_rules_for_services_not_in_config():
    """
    Verifies that gate_services does not change the startup values for services that are not
    part of the config file.
    """
    config = {"nginx": {"autostart": "true"}}

    assert gate_services(config, _cfg()) == []
    assert config == {"nginx": {"autostart": "true"}}


def test_gate_services_keeps_service_on_when_its_rule_raises(monkeypatch, caplog):
    """
    Verifies that a broken rule can never stop a service from starting.
    """
    monkeypatch.setitem(SERVICE_REQUIREMENTS, "gcworker", lambda c: 1 / 0)
    config = registry_services()

    with caplog.at_level(logging.WARNING):
        disabled = gate_services(config, _cfg())

    assert config["gcworker"]["autostart"] == "true"
    assert "gcworker" not in disabled
    assert "gcworker" in caplog.text


def test_gate_services_in_recovery_mode_turns_off_workers_and_builder():
    """
    Verifies that account recovery mode turns off every gated service, including the builder, and
    leaves services that are not gated (nginx) alone.
    """
    config = registry_services()

    gate_services(config, _cfg(ACCOUNT_RECOVERY_MODE=True))

    assert config["gcworker"]["autostart"] == "false"
    assert config["notificationworker"]["autostart"] == "false"
    assert config["builder"]["autostart"] == "false"
    assert config["nginx"]["autostart"] == "true"


def test_gate_services_with_defaults_disables_expected_services():
    """
    Pins the behaviour for a default configuration so unexpected rule changes show up in review.
    """
    config = registry_services()

    disabled = gate_services(config, _cfg())

    assert "autopruneworker" in disabled
    assert "teamsyncworker" in disabled
    assert "gunicorn-secscan" in disabled
    for service in ["gcworker", "notificationworker", "builder", "exportactionlogsworker"]:
        assert service not in disabled


@pytest.fixture
def no_override_config(monkeypatch):
    monkeypatch.delenv("QUAY_OVERRIDE_CONFIG", raising=False)


def test_resolve_effective_config_uses_defaults(no_override_config):
    effective = resolve_effective_config({})

    assert effective == DEFAULTS


def test_resolve_effective_config_accepts_missing_config_yaml(no_override_config):
    assert resolve_effective_config(None) == DEFAULTS


def test_resolve_effective_config_config_yaml_overrides_defaults(no_override_config):
    assert DEFAULTS["FEATURE_AUTO_PRUNE"] is False

    effective = resolve_effective_config({"FEATURE_AUTO_PRUNE": True})

    assert effective["FEATURE_AUTO_PRUNE"] is True
    assert effective["FEATURE_GARBAGE_COLLECTION"] is DEFAULTS["FEATURE_GARBAGE_COLLECTION"]


def test_resolve_effective_config_environment_overrides_config_yaml(monkeypatch):
    monkeypatch.setenv("QUAY_OVERRIDE_CONFIG", json.dumps({"FEATURE_AUTO_PRUNE": False}))

    effective = resolve_effective_config({"FEATURE_AUTO_PRUNE": True})

    assert effective["FEATURE_AUTO_PRUNE"] is False


def test_resolve_effective_config_invalid_override_returns_none(monkeypatch, caplog):
    """
    Verifies the fail-open path: an unparseable QUAY_OVERRIDE_CONFIG means no service gets skipped.
    """
    monkeypatch.setenv("QUAY_OVERRIDE_CONFIG", "{not json")

    with caplog.at_level(logging.WARNING):
        assert resolve_effective_config({"FEATURE_AUTO_PRUNE": True}) is None

    assert "QUAY_OVERRIDE_CONFIG" in caplog.text


def test_resolve_effective_config_returns_none_without_default_config(monkeypatch):
    monkeypatch.setattr(service_gating, "load_default_config", lambda: None)

    assert resolve_effective_config({}) is None


@pytest.mark.parametrize(
    "config",
    [
        '"abc"',
        "[1, 2]",
        "5",
    ],
)
def test_resolve_effective_config_returns_none_when_override_is_not_an_object(
    monkeypatch, no_override_config, config
):
    """
    Verifies that on bad json provided via QUAY_OVERRIDE_CONFIG,
    resolve_effective_config returns a None object.
    """
    monkeypatch.setenv("QUAY_OVERRIDE_CONFIG", config)
    assert resolve_effective_config({}) is None
