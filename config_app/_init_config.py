import os
import re
import subprocess

# Note: this currently points to the directory above, since we're in the quay config_app dir
# TODO(config_extract): revert to root directory rather than the one above
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONF_DIR = os.getenv("QUAYCONF", os.path.join(ROOT_DIR, "conf/"))
STATIC_DIR = os.path.join(ROOT_DIR, "static/")
STATIC_LDN_DIR = os.path.join(STATIC_DIR, "ldn/")
STATIC_FONTS_DIR = os.path.join(STATIC_DIR, "fonts/")
TEMPLATE_DIR = os.path.join(ROOT_DIR, "templates/")
IS_KUBERNETES = "KUBERNETES_SERVICE_HOST" in os.environ


def _get_version_number_changelog():
    try:
        with open(os.path.join(ROOT_DIR, "CHANGELOG.md")) as f:
            return re.search(r"(v[0-9]+\.[0-9]+\.[0-9]+)", f.readline()).group(0)
    except IOError:
        return ""


def _get_git_sha():
    if os.path.exists("GIT_HEAD"):
        with open(os.path.join(ROOT_DIR, "GIT_HEAD")) as f:
            return f.read()
    else:
        try:
            return subprocess.check_output(["git", "rev-parse", "HEAD"]).strip()[0:8]
        except (OSError, subprocess.CalledProcessError):
            pass
    return "unknown"


__version__ = _get_version_number_changelog()
__gitrev__ = _get_git_sha()
