from contextlib import contextmanager

import os
import tempfile

from six import iteritems
from supervisor.options import ServerOptions

import jinja2
import pytest

from ..supervisord_conf_create import (
    registry_services,
    limit_services,
    override_services,
    QUAY_SERVICES,
    QUAY_OVERRIDE_SERVICES,
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
