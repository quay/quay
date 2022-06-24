import os
import os.path
import sys
from typing import Dict, Iterable, Optional, TypedDict, Union

import jinja2

import features
from singletons.authentication import authentication
from singletons.config import app_config

QUAYPATH = os.getenv("QUAYPATH", ".")
QUAYDIR = os.getenv("QUAYDIR", "/")
QUAYCONF_DIR = os.getenv("QUAYCONF", os.path.join(QUAYDIR, QUAYPATH, "conf"))
QUAYRUN_DIR = os.getenv("QUAYRUN", QUAYCONF_DIR)

QUAY_LOGGING = os.getenv("QUAY_LOGGING", "stdout")  # or "syslog"
QUAY_HOTRELOAD: bool = os.getenv("QUAY_HOTRELOAD", "false") == "true"

QUAY_SERVICES: Optional[str] = os.getenv("QUAY_SERVICES")
QUAY_OVERRIDE_SERVICES: Optional[str] = os.getenv("QUAY_OVERRIDE_SERVICES")


class ServiceConfig(TypedDict):
    autostart: str


class Config:
    def __init__(self, services: Dict[str, ServiceConfig]) -> None:
        self._services = services

    def __getitem__(self, key: str) -> ServiceConfig:
        return self._services[key]

    def keys(self) -> Iterable[str]:
        return self._services.keys()

    def add_service(
        self,
        name: str,
        feature_enabled: Union[bool, features.FeatureNameValue],
    ) -> None:
        assert name not in self._services
        if app_config.get("ACCOUNT_RECOVERY_MODE", False):
            autostart = "false"
        elif not feature_enabled:
            autostart = "false"
        else:
            autostart = "true"
        self._services[name] = {
            "autostart": autostart,
        }


def registry_services() -> Config:
    config = Config(
        {
            "buildlogsarchiver": {"autostart": "true"},
            "chunkcleanupworker": {"autostart": "true"},
            "globalpromstats": {"autostart": "true"},
            "notificationworker": {"autostart": "true"},
            "queuecleanupworker": {"autostart": "true"},
            "dnsmasq": {"autostart": "true"},
            "gunicorn-registry": {"autostart": "true"},
            "gunicorn-web": {"autostart": "true"},
            "ip-resolver-update-worker": {"autostart": "true"},
            "memcache": {"autostart": "true"},
            "nginx": {"autostart": "true"},
            "pushgateway": {"autostart": "true"},
            "servicekey": {"autostart": "true"},
            "config-editor": {"autostart": "false"},
        }
    )
    expiredappspecifictoken_configured = app_config.get("EXPIRED_APP_SPECIFIC_TOKEN_GC") is not None
    logrotate_configured = (
        app_config.get("ACTION_LOG_ARCHIVE_PATH") is not None
        and app_config.get("ACTION_LOG_ARCHIVE_LOCATION") is not None
    )
    config.add_service("blobuploadcleanupworker", features.BLOB_UPLOAD_CLEANUP)
    config.add_service("builder", features.BUILD_SUPPORT)
    config.add_service(
        "expiredappspecifictokenworker",
        features.APP_SPECIFIC_TOKENS and expiredappspecifictoken_configured,
    )
    config.add_service("exportactionlogsworker", features.LOG_EXPORT)
    config.add_service("gcworker", features.GARBAGE_COLLECTION)
    config.add_service("gunicorn-secscan", features.SECURITY_SCANNER)
    config.add_service("logrotateworker", features.ACTION_LOG_ROTATION and logrotate_configured)
    config.add_service("manifestbackfillworker", features.MANIFEST_SIZE_BACKFILL)
    config.add_service("namespacegcworker", features.NAMESPACE_GARBAGE_COLLECTION)
    config.add_service("repomirrorworker", features.REPO_MIRROR)
    config.add_service("repositoryactioncounter", features.REPOSITORY_ACTION_COUNTER)
    config.add_service("repositorygcworker", features.REPOSITORY_GARBAGE_COLLECTION)
    config.add_service(
        "securityscanningnotificationworker",
        features.SECURITY_SCANNER and features.SECURITY_NOTIFICATIONS,
    )
    config.add_service("securityworker", features.SECURITY_SCANNER)
    config.add_service("storagereplication", features.STORAGE_REPLICATION)
    config.add_service("teamsyncworker", features.TEAM_SYNCING and authentication.federated_service)
    return config


def config_services() -> Config:
    return Config(
        {
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
            "securityscanningnotificationworker": {"autostart": "false"},
            "config-editor": {"autostart": "true"},
        }
    )


def generate_supervisord_config(
    filename: str, config: Config, logdriver: str, hotreload: bool
) -> None:
    with open(filename + ".jnj") as f:
        template = jinja2.Template(f.read())
    rendered = template.render(config=config, logdriver=logdriver, hotreload=hotreload)

    with open(filename, "w") as f:
        f.write(rendered)


def limit_services(config: Config, enabled_services: Optional[str]) -> None:
    if enabled_services is None:
        return

    for service in list(config.keys()):
        if service in enabled_services:
            config[service]["autostart"] = "true"
        else:
            config[service]["autostart"] = "false"


def override_services(config: Config, override_services: Optional[str]) -> None:
    if override_services is None:
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
    limit_services(config, QUAY_SERVICES)
    override_services(config, QUAY_OVERRIDE_SERVICES)
    generate_supervisord_config(
        os.path.join(QUAYCONF_DIR, "supervisord.conf"),
        config,
        QUAY_LOGGING,
        QUAY_HOTRELOAD,
    )
