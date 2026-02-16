import logging
import os
import os.path
import sys
from typing import Optional

import jinja2

QUAYPATH = os.getenv("QUAYPATH", ".")
QUAYDIR = os.getenv("QUAYDIR", "/")
QUAYCONF_DIR = os.getenv("QUAYCONF", os.path.join(QUAYDIR, QUAYPATH, "conf"))
QUAYRUN_DIR = os.getenv("QUAYRUN", QUAYCONF_DIR)

logger = logging.getLogger(__name__)

QUAY_LOGGING = os.getenv("QUAY_LOGGING", "stdout")  # or "syslog"
QUAY_HOTRELOAD: bool = os.getenv("QUAY_HOTRELOAD", "false") == "true"

QUAY_SERVICES: Optional[str] = os.getenv("QUAY_SERVICES")
QUAY_OVERRIDE_SERVICES: Optional[str] = os.getenv("QUAY_OVERRIDE_SERVICES")

_FEDERATED_AUTH_TYPES = {"LDAP", "JWT", "Keystone", "OIDC"}

# Maps supervisord service names to lambdas that return True when the worker
# should be enabled.  Defaults in each lambda match config.py:DefaultConfig.
WORKER_FEATURE_GATES = {
    "builder": lambda c: c.get("FEATURE_BUILD_SUPPORT", True),
    "gcworker": lambda c: c.get("FEATURE_GARBAGE_COLLECTION", True)
    and not c.get("DISABLE_PUSHES", False),
    "namespacegcworker": lambda c: c.get("FEATURE_NAMESPACE_GARBAGE_COLLECTION", True)
    and not c.get("DISABLE_PUSHES", False),
    "repositorygcworker": lambda c: c.get("FEATURE_REPOSITORY_GARBAGE_COLLECTION", True)
    and not c.get("DISABLE_PUSHES", False),
    "securityworker": lambda c: c.get("FEATURE_SECURITY_SCANNER", False),
    "gunicorn-secscan": lambda c: c.get("FEATURE_SECURITY_SCANNER", False),
    "securityscanningnotificationworker": (
        lambda c: c.get("FEATURE_SECURITY_SCANNER", False)
        and c.get("FEATURE_SECURITY_NOTIFICATIONS", False)
    ),
    "repomirrorworker": lambda c: c.get("FEATURE_REPO_MIRROR", False),
    "storagereplication": lambda c: c.get("FEATURE_STORAGE_REPLICATION", False),
    "teamsyncworker": (
        lambda c: c.get("FEATURE_TEAM_SYNCING", False)
        and c.get("AUTHENTICATION_TYPE", "Database") in _FEDERATED_AUTH_TYPES
    ),
    "exportactionlogsworker": lambda c: c.get("FEATURE_LOG_EXPORT", True),
    "expiredappspecifictokenworker": (
        lambda c: c.get("FEATURE_APP_SPECIFIC_TOKENS", True)
        and c.get("EXPIRED_APP_SPECIFIC_TOKEN_GC") is not None
    ),
    "logrotateworker": (
        lambda c: c.get("FEATURE_ACTION_LOG_ROTATION", False)
        and c.get("ACTION_LOG_ARCHIVE_PATH") is not None
        and c.get("ACTION_LOG_ARCHIVE_LOCATION") is not None
    ),
    "manifestbackfillworker": lambda c: c.get("FEATURE_MANIFEST_SIZE_BACKFILL", True),
    "manifestsubjectbackfillworker": lambda c: c.get("FEATURE_MANIFEST_SUBJECT_BACKFILL", True),
    "repositoryactioncounter": lambda c: c.get("FEATURE_REPOSITORY_ACTION_COUNTER", True),
    "quotatotalworker": lambda c: c.get("FEATURE_QUOTA_MANAGEMENT", False)
    and c.get("QUOTA_BACKFILL", True),
    "quotaregistrysizeworker": lambda c: c.get("FEATURE_QUOTA_MANAGEMENT", False),
    "autopruneworker": lambda c: c.get("FEATURE_AUTO_PRUNE", False),
    "reconciliationworker": lambda c: c.get("FEATURE_ENTITLEMENT_RECONCILIATION", False),
    "proxycacheblobworker": lambda c: c.get("FEATURE_PROXY_CACHE", False)
    and c.get("FEATURE_PROXY_CACHE_BLOB_DOWNLOAD", True),
    "pullstatsredisflushworker": (
        lambda c: c.get("FEATURE_IMAGE_PULL_STATS", False)
        and c.get("PULL_METRICS_REDIS") is not None
    ),
    "globalpromstats": lambda c: c.get("PROMETHEUS_PUSHGATEWAY_URL") is not None,
    "chunkcleanupworker": (
        lambda c: "SwiftStorage"
        in [v[0] for v in c.get("DISTRIBUTED_STORAGE_CONFIG", {}).values() if v]
    ),
}


def registry_services():
    return {
        "blobuploadcleanupworker": {"autostart": "true"},
        "buildlogsarchiver": {"autostart": "true"},
        "builder": {"autostart": "true"},
        "chunkcleanupworker": {"autostart": "true"},
        "expiredappspecifictokenworker": {"autostart": "true"},
        "exportactionlogsworker": {"autostart": "true"},
        "gcworker": {"autostart": "true"},
        "globalpromstats": {"autostart": "true"},
        "logrotateworker": {"autostart": "true"},
        "namespacegcworker": {"autostart": "true"},
        "repositorygcworker": {"autostart": "true"},
        "notificationworker": {"autostart": "true"},
        "queuecleanupworker": {"autostart": "true"},
        "reconciliationworker": {"autostart": "true"},
        "repositoryactioncounter": {"autostart": "true"},
        "securityworker": {"autostart": "true"},
        "storagereplication": {"autostart": "true"},
        "teamsyncworker": {"autostart": "true"},
        "dnsmasq": {"autostart": "true"},
        "gunicorn-registry": {"autostart": "true"},
        "gunicorn-secscan": {"autostart": "true"},
        "gunicorn-web": {"autostart": "true"},
        "ip-resolver-update-worker": {"autostart": "true"},
        "memcache": {"autostart": "true"},
        "nginx": {"autostart": "true"},
        "pushgateway": {"autostart": "true"},
        "servicekey": {"autostart": "true"},
        "repomirrorworker": {"autostart": "false"},
        "manifestbackfillworker": {"autostart": "true"},
        "manifestsubjectbackfillworker": {"autostart": "true"},
        "securityscanningnotificationworker": {"autostart": "true"},
        "quotatotalworker": {"autostart": "true"},
        "quotaregistrysizeworker": {"autostart": "true"},
        "autopruneworker": {"autostart": "true"},
        "proxycacheblobworker": {"autostart": "true"},
        "pullstatsredisflushworker": {"autostart": "true"},
    }


def config_services():
    return {
        "blobuploadcleanupworker": {"autostart": "false"},
        "buildlogsarchiver": {"autostart": "false"},
        "builder": {"autostart": "false"},
        "chunkcleanupworker": {"autostart": "false"},
        "expiredappspecifictokenworker": {"autostart": "false"},
        "exportactionlogsworker": {"autostart": "false"},
        "gcworker": {"autostart": "false"},
        "globalpromstats": {"autostart": "false"},
        "logrotateworker": {"autostart": "false"},
        "namespacegcworker": {"autostart": "false"},
        "repositorygcworker": {"autostart": "false"},
        "notificationworker": {"autostart": "false"},
        "queuecleanupworker": {"autostart": "false"},
        "repositoryactioncounter": {"autostart": "false"},
        "reconciliationworker": {"autostart": "false"},
        "securityworker": {"autostart": "false"},
        "storagereplication": {"autostart": "false"},
        "teamsyncworker": {"autostart": "false"},
        "dnsmasq": {"autostart": "false"},
        "gunicorn-registry": {"autostart": "false"},
        "gunicorn-secscan": {"autostart": "false"},
        "gunicorn-web": {"autostart": "false"},
        "ip-resolver-update-worker": {"autostart": "false"},
        "memcache": {"autostart": "false"},
        "nginx": {"autostart": "false"},
        "pushgateway": {"autostart": "false"},
        "servicekey": {"autostart": "false"},
        "repomirrorworker": {"autostart": "false"},
        "manifestbackfillworker": {"autostart": "false"},
        "manifestsubjectbackfillworker": {"autostart": "false"},
        "securityscanningnotificationworker": {"autostart": "false"},
        "quotatotalworker": {"autostart": "false"},
        "quotaregistrysizeworker": {"autostart": "false"},
        "autopruneworker": {"autostart": "false"},
        "proxycacheblobworker": {"autostart": "false"},
        "pullstatsredisflushworker": {"autostart": "false"},
    }


def _load_quay_config():
    """Load Quay config from YAML without importing Flask."""
    try:
        from _init import config_provider

        config = {}
        if config_provider:
            yaml_config = config_provider.get_config()
            if yaml_config:
                config.update(yaml_config)
        # Apply QUAY_FEATURE_* env var overrides
        for key, value in os.environ.items():
            if key.startswith("QUAY_FEATURE_"):
                feature_key = "FEATURE_" + key[len("QUAY_FEATURE_") :]
                config[feature_key] = value.lower() in ("true", "1", "yes")
        return config
    except Exception as e:
        logger.warning("Failed to load Quay config, falling back to fail-open: %s", e)
        return None  # Fail-open: all workers start (current behavior)


def _apply_feature_gates(services, quay_config):
    """Disable workers whose feature flags are off.

    Runs before limit/override so operators can always force-enable
    a worker via QUAY_SERVICES or QUAY_OVERRIDE_SERVICES.
    """
    if quay_config is None:
        return

    if quay_config.get("ACCOUNT_RECOVERY_MODE", False):
        for service in WORKER_FEATURE_GATES:
            if service in services:
                services[service]["autostart"] = "false"
        return

    for service, gate_fn in WORKER_FEATURE_GATES.items():
        if service in services and not gate_fn(quay_config):
            services[service]["autostart"] = "false"


def generate_supervisord_config(filename, config, logdriver, hotreload):
    with open(filename + ".jnj") as f:
        template = jinja2.Template(f.read())
    rendered = template.render(config=config, logdriver=logdriver, hotreload=hotreload)

    with open(filename, "w") as f:
        f.write(rendered)


def limit_services(config, enabled_services):
    if not enabled_services:
        return

    for service in list(config.keys()):
        if service in enabled_services:
            config[service]["autostart"] = "true"
        else:
            config[service]["autostart"] = "false"


def override_services(config, override_services):
    if not override_services:
        return

    for service in list(config.keys()):
        if service + "=true" in override_services:
            config[service]["autostart"] = "true"
        elif service + "=false" in override_services:
            config[service]["autostart"] = "false"


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "config":
        config = config_services()
    else:
        config = registry_services()

    quay_config = _load_quay_config()
    _apply_feature_gates(config, quay_config)
    limit_services(config, QUAY_SERVICES)
    override_services(config, QUAY_OVERRIDE_SERVICES)

    generate_supervisord_config(
        os.path.join(QUAYCONF_DIR, "supervisord.conf"),
        config,
        QUAY_LOGGING,
        QUAY_HOTRELOAD,
    )
