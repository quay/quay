import os
import os.path

import jinja2

QUAYPATH = os.getenv("QUAYPATH", ".")
QUAYDIR = os.getenv("QUAYDIR", "/")
QUAYCONF_DIR = os.getenv("QUAYCONF", os.path.join(QUAYDIR, QUAYPATH, "conf"))

QUAY_LOGGING = os.getenv("QUAY_LOGGING", "stdout")  # or "syslog"

QUAY_SERVICES = os.getenv("QUAY_SERVICES", [])
QUAY_OVERRIDE_SERVICES = os.getenv("QUAY_OVERRIDE_SERVICES", [])


def default_services():
    return {
        "blobuploadcleanupworker": {"autostart": "true"},
        "buildlogsarchiver": {"autostart": "true"},
        "builder": {"autostart": "true"},
        "chunkcleanupworker": {"autostart": "true"},
        "expiredappspecifictokenworker": {"autostart": "true"},
        "exportactionlogsworker": {"autostart": "true"},
        "gcworker": {"autostart": "true"},
        "globalpromstats": {"autostart": "true"},
        "labelbackfillworker": {"autostart": "true"},
        "logrotateworker": {"autostart": "true"},
        "namespacegcworker": {"autostart": "true"},
        "repositorygcworker": {"autostart": "true"},
        "notificationworker": {"autostart": "true"},
        "queuecleanupworker": {"autostart": "true"},
        "repositoryactioncounter": {"autostart": "true"},
        "security_notification_worker": {"autostart": "true"},
        "securityworker": {"autostart": "true"},
        "storagereplication": {"autostart": "true"},
        "tagbackfillworker": {"autostart": "true"},
        "teamsyncworker": {"autostart": "true"},
        "dnsmasq": {"autostart": "true"},
        "gunicorn-registry": {"autostart": "true"},
        "gunicorn-secscan": {"autostart": "true"},
        "gunicorn-verbs": {"autostart": "true"},
        "gunicorn-web": {"autostart": "true"},
        "ip-resolver-update-worker": {"autostart": "true"},
        "jwtproxy": {"autostart": "true"},
        "memcache": {"autostart": "true"},
        "nginx": {"autostart": "true"},
        "pushgateway": {"autostart": "true"},
        "servicekey": {"autostart": "true"},
        "repomirrorworker": {"autostart": "false"},
    }


def generate_supervisord_config(filename, config, logdriver):
    with open(filename + ".jnj") as f:
        template = jinja2.Template(f.read())
    rendered = template.render(config=config, logdriver=logdriver)

    with open(filename, "w") as f:
        f.write(rendered)


def limit_services(config, enabled_services):
    if enabled_services == []:
        return

    for service in list(config.keys()):
        if service in enabled_services:
            config[service]["autostart"] = "true"
        else:
            config[service]["autostart"] = "false"


def override_services(config, override_services):
    if override_services == []:
        return

    for service in list(config.keys()):
        if service + "=true" in override_services:
            config[service]["autostart"] = "true"
        elif service + "=false" in override_services:
            config[service]["autostart"] = "false"


if __name__ == "__main__":
    config = default_services()
    limit_services(config, QUAY_SERVICES)
    override_services(config, QUAY_OVERRIDE_SERVICES)
    generate_supervisord_config(
        os.path.join(QUAYCONF_DIR, "supervisord.conf"), config, QUAY_LOGGING,
    )
