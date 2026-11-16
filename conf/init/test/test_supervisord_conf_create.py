import json
import os
import re
import shutil
import subprocess
import sys
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

    def test_config_yaml_reaches_gunicorn_commands(self, tmp_path):
        """Exercise load_app_config() and the __main__ wiring end-to-end via a real config.yaml."""
        quay_conf_dir = tmp_path / "conf"
        (quay_conf_dir / "stack").mkdir(parents=True)
        (quay_conf_dir / "stack" / "config.yaml").write_text(
            "GUNICORN_REGISTRY_TIMEOUT: 111\nGUNICORN_WEB_TIMEOUT: 45\n"
        )

        repo_conf_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..")
        shutil.copy(
            os.path.join(repo_conf_dir, "supervisord.conf.jnj"),
            quay_conf_dir / "supervisord.conf.jnj",
        )

        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "../supervisord_conf_create.py"
        )

        env = os.environ.copy()
        env.update(
            QUAYDIR=str(tmp_path),
            QUAYPATH=".",
            QUAYCONF=str(quay_conf_dir),
            QUAY_SERVICES="",
            QUAY_OVERRIDE_SERVICES="",
            QUAY_LOGGING="stdout",
            QUAY_HOTRELOAD="false",
        )

        subprocess.run([sys.executable, script_path], env=env, check=True)

        rendered = (quay_conf_dir / "supervisord.conf").read_text()

        registry_match = re.search(r"gunicorn --timeout=(\d+) -c .+gunicorn_registry\.py", rendered)
        assert registry_match is not None
        assert registry_match.group(1) == "111"

        web_match = re.search(r"gunicorn --timeout=(\d+) -c .+gunicorn_web\.py", rendered)
        assert web_match is not None
        assert web_match.group(1) == "45"


def _render_with_script(tmp_path, config_yaml, **extra_env):
    """
    Helper function that runs supervisord_conf_create.py against a temporary directory and
    returns supervisord.conf file.
    """
    quay_config_dir = tmp_path.joinpath("conf")
    stack_path = quay_config_dir.joinpath("stack")

    stack_path.mkdir(parents=True)

    config_file = stack_path.joinpath("config.yaml")
    config_file.write_text(config_yaml)

    here = os.path.dirname(os.path.abspath(__file__))

    shutil.copy(
        os.path.join(
            here,
            "..",
            "..",
            "supervisord.conf.jnj",
        ),
        quay_config_dir.joinpath("supervisord.conf.jnj"),
    )

    env = os.environ.copy()

    # don't inherit the dev override, remove it from env. variables
    env.pop("QUAY_OVERRIDE_CONFIG", None)

    env.update(
        QUAYDIR=str(tmp_path),
        QUAYPATH=".",
        QUAYCONF=str(quay_config_dir),
        QUAY_SERVICES="",
        QUAY_OVERRIDE_SERVICES="",
        QUAY_LOGGING="stdout",
        QUAY_HOTRELOAD="false",
    )
    env.update(extra_env)

    script_path = os.path.join(here, "..", "supervisord_conf_create.py")

    subprocess.run([sys.executable, script_path], env=env, check=True)
    return quay_config_dir.joinpath("supervisord.conf").read_text()


def _autostart(rendered, program):
    """
    Helper that detects when a specific program section starts and ends (either at the start of
    next program section or runs to the end of file).
    """
    section = re.search(
        r"\[program:%s\](.*?)(?=^\[|\Z)" % re.escape(program),
        rendered,
        re.DOTALL | re.MULTILINE,
    )
    assert section is not None, "no [program:%s] section" % program
    match = re.search(
        r"^autostart = (\w+)",
        section.group(1),
        re.MULTILINE,
    )

    assert match is not None, "no autostart line in [program:%s]" % program

    return match.group(1)


class TestRenderSupervisorDConf:
    @pytest.mark.parametrize(
        ("config_yaml", "env", "expected"),
        [
            pytest.param("", {}, {"securityworker": "false", "nginx": "true"}, id="feature-off"),
            pytest.param(
                "FEATURE_SECURITY_SCANNER: true\n",
                {},
                {"securityworker": "true", "nginx": "true"},
                id="feature-on",
            ),
            pytest.param(
                "FEATURE_SECURITY_SCANNER: true\nFEATURE_AUTO_PRUNE: true\n",
                {},
                {"securityworker": "true", "nginx": "true", "autopruneworker": "true"},
                id="multiple-features-on",
            ),
            pytest.param(
                "",
                {},
                {"nginx": "true", "gunicorn-registry": "true", "gunicorn-web": "true"},
                id="default-services-always-on",
            ),
            pytest.param(
                "",
                {"QUAY_OVERRIDE_SERVICES": "securityworker=true"},
                {"securityworker": "true"},
                id="override-services-wins-securityworker-true",
            ),
            pytest.param(
                "FEATURE_SECURITY_SCANNER: true\n",
                {"QUAY_OVERRIDE_SERVICES": "securityworker=false"},
                {"securityworker": "false"},
                id="override-services-wins-securityworker-false",
            ),
            pytest.param(
                "",
                {"QUAY_OVERRIDE_CONFIG": json.dumps({"FEATURE_SECURITY_SCANNER": True})},
                {"securityworker": "true"},
                id="override-config-is-honored-securityworker-true",
            ),
            pytest.param(
                "FEATURE_SECURITY_SCANNER: true\n",
                {"QUAY_OVERRIDE_CONFIG": json.dumps({"FEATURE_SECURITY_SCANNER": False})},
                {"securityworker": "false"},
                id="override-config-wins-over-securityworker-false",
            ),
            pytest.param(
                "",
                {"QUAY_OVERRIDE_CONFIG": "{not json"},
                {"securityworker": "true"},
                id="invalid-override-config-enables-all-workers",
            ),
        ],
    )
    def test_autostart(self, tmp_path, config_yaml, env, expected):
        """
        Verifies that proper services are marked to autostart after config read.
        """
        rendered = _render_with_script(tmp_path, config_yaml, **env)
        for program, value in expected.items():
            assert _autostart(rendered, program) == value, program

    def test_quay_services_allowlist_wins_over_gating(self, tmp_path):
        """
        Verifies that the service allow list wins over the provided configuration.
        """
        rendered = _render_with_script(
            tmp_path, "", QUAY_SERVICES="repomirrorworker,securityworker,nginx"
        )

        # only listed services should be started
        assert _autostart(rendered, "repomirrorworker") == "true"
        assert _autostart(rendered, "securityworker") == "true"
        assert _autostart(rendered, "nginx") == "true"

        # everything else should be turned off, even services that are usually not
        assert _autostart(rendered, "gunicorn-web") == "false"
