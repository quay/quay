import os
import re
import tempfile
from contextlib import contextmanager

import jinja2
import pytest
from six import iteritems
from supervisor.options import ServerOptions

from ..supervisord_conf_create import (
    MAX_GUNICORN_TIMEOUT,
    QUAY_OVERRIDE_SERVICES,
    QUAY_SERVICES,
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


def render_supervisord_conf(config, **extra_vars):
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../supervisord.conf.jnj")
    ) as f:
        template = jinja2.Template(f.read())
    return template.render(config=config, **extra_vars)


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


class TestGunicornTimeouts:
    def test_registry_timeout_default(self):
        config = registry_services()
        rendered = render_supervisord_conf(config)
        match = re.search(r"gunicorn --timeout=(\d+) -c .+gunicorn_registry\.py", rendered)
        assert match is not None, "gunicorn-registry should have --timeout flag"
        assert match.group(1) == "30"

    def test_registry_timeout_custom(self):
        config = registry_services()
        rendered = render_supervisord_conf(config, gunicorn_registry_timeout=300)
        match = re.search(r"gunicorn --timeout=(\d+) -c .+gunicorn_registry\.py", rendered)
        assert match is not None
        assert match.group(1) == "300"

    def test_web_timeout_default(self):
        config = registry_services()
        rendered = render_supervisord_conf(config)
        match = re.search(r"gunicorn --timeout=(\d+) -c .+gunicorn_web\.py", rendered)
        assert match is not None, "gunicorn-web should have --timeout flag"
        assert match.group(1) == "30"

    def test_web_timeout_custom(self):
        config = registry_services()
        rendered = render_supervisord_conf(config, gunicorn_web_timeout=120)
        match = re.search(r"gunicorn --timeout=(\d+) -c .+gunicorn_web\.py", rendered)
        assert match is not None
        assert match.group(1) == "120"

    def test_web_timeout_hotreload_uses_600(self):
        config = registry_services()
        rendered = render_supervisord_conf(config, hotreload=True, gunicorn_web_timeout=120)
        match = re.search(r"gunicorn --timeout=(\d+) -c .+gunicorn_web\.py", rendered)
        assert match is not None
        assert match.group(1) == "600", "hotreload mode should use 600s timeout regardless"

    def test_registry_timeout_clamped_to_max(self):
        config = registry_services()
        rendered = render_supervisord_conf(
            config, gunicorn_registry_timeout=min(7200, MAX_GUNICORN_TIMEOUT)
        )
        match = re.search(r"gunicorn --timeout=(\d+) -c .+gunicorn_registry\.py", rendered)
        assert match is not None
        assert match.group(1) == str(MAX_GUNICORN_TIMEOUT)

    def test_web_timeout_clamped_to_max(self):
        config = registry_services()
        rendered = render_supervisord_conf(
            config, gunicorn_web_timeout=min(7200, MAX_GUNICORN_TIMEOUT)
        )
        match = re.search(r"gunicorn --timeout=(\d+) -c .+gunicorn_web\.py", rendered)
        assert match is not None
        assert match.group(1) == str(MAX_GUNICORN_TIMEOUT)

    def test_max_gunicorn_timeout_is_300(self):
        assert MAX_GUNICORN_TIMEOUT == 300
