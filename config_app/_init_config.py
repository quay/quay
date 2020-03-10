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


def _get_version():
    """
    Version is determined in following order:
    1. First non-blank line VERSION file
    2. environment variable QUAY_VERSION
    3. GIT_HEAD file
    4. git rev-parse HEAD
    """
    version = ""
    if os.path.exists(os.path.join(ROOT_DIR, "VERSION")):
        with open(os.path.join(ROOT_DIR, "VERSION")) as f:
            for line in f:
                if line != "":
                    version = line.strip()
                    break
    if not version or version == "":
        version = os.environ.get("QUAY_VERSION", "")
    if not version or version == "":
        version = _get_git_sha()

    return version


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


__version__ = _get_version()
__gitrev__ = _get_git_sha()
