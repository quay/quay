import os
import os.path
import sys
from typing import List

import jinja2
import yaml

QUAYPATH = os.getenv("QUAYPATH", ".")
QUAYDIR = os.getenv("QUAYDIR", "/")
QUAYCONF_DIR = os.getenv("QUAYCONF", os.path.join(QUAYDIR, QUAYPATH, "conf"))
QUAYRUN_DIR = os.getenv("QUAYRUN", QUAYCONF_DIR)

QUAY_LOGGING = os.getenv("QUAY_LOGGING", "stdout")  # or "syslog"
QUAY_HOTRELOAD: bool = os.getenv("QUAY_HOTRELOAD", "false") == "true"

MAX_GUNICORN_TIMEOUT = 300


def _parse_csv_env(name):
    val = os.getenv(name, "")
    return [s.strip() for s in val.split(",") if s.strip()] if val else []


QUAY_SERVICES: List[str] = _parse_csv_env("QUAY_SERVICES")
QUAY_OVERRIDE_SERVICES: List[str] = _parse_csv_env("QUAY_OVERRIDE_SERVICES")


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


def load_app_config():
    config_path = os.path.join(QUAYCONF_DIR, "stack/config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


def generate_supervisord_config(filename, config, logdriver, hotreload, **extra_vars):
    with open(filename + ".jnj") as f:
        template = jinja2.Template(f.read())
    rendered = template.render(
        config=config, logdriver=logdriver, hotreload=hotreload, **extra_vars
    )

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
    config = registry_services()
    limit_services(config, QUAY_SERVICES)
    override_services(config, QUAY_OVERRIDE_SERVICES)

    app_config = load_app_config()

    generate_supervisord_config(
        os.path.join(QUAYCONF_DIR, "supervisord.conf"),
        config,
        QUAY_LOGGING,
        QUAY_HOTRELOAD,
        gunicorn_registry_timeout=min(
            app_config.get("GUNICORN_REGISTRY_TIMEOUT", 30), MAX_GUNICORN_TIMEOUT
        ),
        gunicorn_web_timeout=min(app_config.get("GUNICORN_WEB_TIMEOUT", 30), MAX_GUNICORN_TIMEOUT),
    )
