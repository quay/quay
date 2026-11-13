import json
import logging
import os
import sys

logger = logging.getLogger(__name__)


def _feature(cfg, name):
    """
    Checks which features are enabled based on the provided configuration.
    """
    value = cfg.get(name, False)
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def _storage_engines(cfg):
    """
    Detects what storage engines we have defined based on the provided
    configuration.
    """
    engines = {entry[0] for entry in (cfg.get("DISTRIBUTED_STORAGE_CONFIG") or {}).values()}
    return engines


def _pushes_enabled(cfg):
    return not cfg.get("DISABLE_PUSHES", False)


def _registry_read_only(cfg):
    return cfg.get("REGISTRY_STATE") == "readonly"


def secscan_enabled(cfg):
    return (
        _feature(cfg, "FEATURE_SECURITY_SCANNER")
        and _feature(cfg, "FEATURE_SECURITY_NOTIFICATIONS")
        and not cfg.get("ACCOUNT_RECOVERY_MODE", False)
    )


def _log_archive_configured(cfg):
    return bool(
        cfg.get("ACTION_LOG_ARCHIVE_PATH", None) is not None
        and cfg.get("ACTION_LOG_ARCHIVE_LOCATION", None) is not None
    )


def _pull_stats_redis_enabled(cfg):
    return bool(cfg.get("PULL_METRICS_REDIS", None) and not cfg.get("TESTING", True))


def _builder_needed(cfg):
    if _feature(cfg, "FEATURE_BUILD_SUPPORT"):
        build_manager = cfg.get("BUILD_MANAGER", None)
        if (
            build_manager is not None
            and build_manager[0] != "external"
            and not _registry_read_only(cfg)
        ):
            return True
    return False


# Services that need to start based on enabled features
SERVICE_REQUIREMENTS = {
    "autopruneworker": lambda c: _feature(c, "FEATURE_AUTO_PRUNE"),
    "exportactionlogsworker": lambda c: _feature(c, "FEATURE_LOG_EXPORT"),
    "manifestbackfillworker": lambda c: _feature(c, "FEATURE_MANIFEST_SIZE_BACKFILL"),
    "manifestsubjectbackfillworker": lambda c: _feature(c, "FEATURE_MANIFEST_SUBJECT_BACKFILL"),
    "quotaregistrysizeworker": lambda c: _feature(c, "FEATURE_QUOTA_MANAGEMENT"),
    "reconciliationworker": lambda c: _feature(c, "FEATURE_ENTITLEMENT_RECONCILIATION"),
    "repositoryactioncounter": lambda c: _feature(c, "FEATURE_REPOSITORY_ACTION_COUNTER"),
    "securityworker": lambda c: _feature(c, "FEATURE_SECURITY_SCANNER"),
    "gcworker": lambda c: _feature(c, "FEATURE_GARBAGE_COLLECTION") and _pushes_enabled(c),
    "repositorygcworker": lambda c: _feature(c, "FEATURE_REPOSITORY_GARBAGE_COLLECTION")
    and _pushes_enabled(c),
    "namespacegcworker": lambda c: _feature(c, "FEATURE_NAMESPACE_GARBAGE_COLLECTION")
    and _pushes_enabled(c),
    "securityscanningnotificationworker": lambda c: _feature(c, "FEATURE_SECURITY_SCANNER")
    and _feature(c, "FEATURE_SECURITY_NOTIFICATIONS"),
    "gunicorn-secscan": lambda c: secscan_enabled(c),
    "proxycacheblobworker": lambda c: _feature(c, "FEATURE_PROXY_CACHE")
    and _feature(c, "FEATURE_PROXY_CACHE_BLOB_DOWNLOAD"),
    "quotatotalworker": lambda c: _feature(c, "FEATURE_QUOTA_MANAGEMENT")
    and c.get("QUOTA_BACKFILL", True),
    "storagereplication": lambda c: _feature(c, "FEATURE_STORAGE_REPLICATION")
    and "LocalStorage" not in _storage_engines(c),
    "chunkcleanupworker": lambda c: "SwiftStorage" in _storage_engines(c),
    "teamsyncworker": lambda c: _feature(c, "FEATURE_TEAM_SYNCING")
    and c.get("AUTHENTICATION_TYPE", "Database") in ["LDAP", "Keystone"],
    "logrotateworker": lambda c: _feature(c, "FEATURE_ACTION_LOG_ROTATION")
    and _log_archive_configured(c),
    "expiredappspecifictokenworker": lambda c: _feature(c, "FEATURE_APP_SPECIFIC_TOKENS")
    and c.get("EXPIRED_APP_SPECIFIC_TOKEN_GC", None) is not None,
    "pullstatsredisflushworker": lambda c: _feature(c, "FEATURE_IMAGE_PULL_STATS")
    and _pull_stats_redis_enabled(c),
    "blobuploadcleanupworker": lambda c: True,
    "notificationworker": lambda c: True,
    "queuecleanupworker": lambda c: True,
    "builder": lambda c: _builder_needed(c),
}


def load_default_config():
    """
    Loads the default config provided by the config.py file.
    """
    root = os.path.abspath(
        os.path.join(
            os.path.dirname(
                os.path.abspath(__file__),
            ),
            "../..",
        )
    )

    if root not in sys.path:
        sys.path.insert(0, root)

    try:
        from config import DefaultConfig
    except Exception as exc:
        logger.warning("Unable to load default config: %s", exc)
        return None

    services = {key: getattr(DefaultConfig, key) for key in dir(DefaultConfig) if key.isupper()}

    return services


def resolve_effective_config(app_config):
    """
    Builds the effective configuration based on default options, the options provided through
    the config.yaml file and the override configuration provided through the environment.
    """
    effective_config = load_default_config()
    if effective_config is None:
        return None

    # update effective_config dict with the values from app_config (config.yaml file)
    effective_config.update(app_config or {})

    # update the effective_config with the values from the env.
    try:
        overrides = json.loads(os.getenv("QUAY_OVERRIDE_CONFIG", "{}"))
    except ValueError as e:
        logger.warning("Invalid QUAY_OVERRIDE_CONFIG: %s", e)
        logger.warning("Starting all services.")
        return None

    effective_config.update(overrides or {})

    return effective_config


def gate_services(config, effective_config):
    """
    Returns a list of services that need to be disabled based on the provided and effective configuration.
    """
    # if there is no effective configuration, assume we need to start all services
    if effective_config is None:
        return []

    recovery = bool(effective_config.get("ACCOUNT_RECOVERY_MODE", False))
    disabled = []

    for service, needed in SERVICE_REQUIREMENTS.items():
        # if the service name is not part of the registry config, skip
        if service not in config:
            continue

        try:
            # attempt to determine if the service is part of our effective config
            # if an exception is raised, log and continue (startup must always succeed, better to
            # start more services, than to stop the registry from starting)
            required = needed(effective_config)
        except Exception as exc:
            logger.warning("Unable to evaluate startup rule for %s: %s", service, exc)
            continue

        # if the registry is in recovery mode and the service in question is not the builder service,
        # mark the service as not required
        if recovery and service != "builder":
            required = False

        # if the service is marked as not required, skip startup of selected service
        if not required:
            config[service]["autostart"] = "false"
            disabled.append(service)

    return disabled
