import os
import re
import shutil

import jinja2
import pytest

from .. import nginx_conf_create


def render_server_base_conf(**kwargs):
    template_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "../../nginx/server-base.conf.jnj",
    )
    with open(template_path) as f:
        template = jinja2.Template(f.read())

    defaults = dict(
        static_dir="/quay-registry/static",
        default_ui="react",
        signing_enabled=False,
        maximum_layer_size="20G",
        enable_rate_limits=False,
        manifests_endpoint_read_timeout=None,
    )
    defaults.update(kwargs)
    return template.render(**defaults)


class TestErrorPageDirective:
    def test_error_page_502_uses_uri_not_absolute_path(self):
        rendered = render_server_base_conf()
        assert "error_page 502 =502 /502.html;" in rendered

    def test_error_page_502_does_not_use_static_dir_path(self):
        rendered = render_server_base_conf()
        assert "error_page 502 /quay-registry/static/502.html" not in rendered

    def test_502_location_block_exists(self):
        rendered = render_server_base_conf()
        assert "location = /502.html {" in rendered

    def test_502_location_uses_correct_root(self):
        rendered = render_server_base_conf()
        match = re.search(r"location = /502\.html \{[^}]*root\s+([^;]+);", rendered, re.DOTALL)
        assert match is not None, "502 location block must have a root directive"
        assert match.group(1).strip() == "/quay-registry/static"

    def test_502_location_is_internal(self):
        rendered = render_server_base_conf()
        match = re.search(r"location = /502\.html \{([^}]*)}", rendered, re.DOTALL)
        assert match is not None
        assert "internal;" in match.group(1)

    def test_502_preserves_status_code(self):
        rendered = render_server_base_conf()
        assert "=502" in rendered

    @pytest.mark.parametrize(
        "static_dir",
        [
            "/quay-registry/static",
            "/custom/path/static",
            "/opt/quay/static",
        ],
    )
    def test_502_location_root_matches_static_dir(self, static_dir):
        rendered = render_server_base_conf(static_dir=static_dir)
        match = re.search(r"location = /502\.html \{[^}]*root\s+([^;]+);", rendered, re.DOTALL)
        assert match is not None
        assert match.group(1).strip() == static_dir

    def test_502_path_resolution_avoids_patternfly_root(self):
        """Regression test: the root location uses static_dir/patternfly/ as root.
        The 502 error page must NOT be resolved through that location's root,
        which would produce a doubled path like
        /quay-registry/static/patternfly/quay-registry/static/502.html."""
        rendered = render_server_base_conf()
        assert "patternfly" not in re.search(
            r"location = /502\.html \{([^}]*)}", rendered, re.DOTALL
        ).group(1)


def render_hosted_http_base_conf(tmp_path, monkeypatch, config):
    os.mkdir(tmp_path / "nginx")
    shutil.copy(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../../nginx/hosted-http-base.conf.jnj",
        ),
        tmp_path / "nginx",
    )
    monkeypatch.setattr(nginx_conf_create, "QUAYCONF_DIR", str(tmp_path))
    nginx_conf_create.generate_hosted_http_base_config(config)
    return (tmp_path / "nginx/hosted-http-base.conf").read_text()


def _listen_lines(rendered):
    return [line.strip() for line in rendered.splitlines() if line.strip().startswith("listen")]


class TestHostedHttpBaseListen:
    def test_ipv4_by_default(self, tmp_path, monkeypatch):
        rendered = render_hosted_http_base_conf(tmp_path, monkeypatch, None)
        assert _listen_lines(rendered) == ["listen 8080 default_server;"]

    def test_ipv6(self, tmp_path, monkeypatch):
        rendered = render_hosted_http_base_conf(
            tmp_path, monkeypatch, {"FEATURE_LISTEN_IP_VERSION": "IPv6"}
        )
        assert _listen_lines(rendered) == ["listen [::]:8080 default_server;"]

    def test_dual_stack(self, tmp_path, monkeypatch):
        rendered = render_hosted_http_base_conf(
            tmp_path, monkeypatch, {"FEATURE_LISTEN_IP_VERSION": "dual-stack"}
        )
        assert _listen_lines(rendered) == [
            "listen 8080 default_server;",
            "listen [::]:8080 default_server;",
        ]

    def test_dual_stack_with_proxy_protocol(self, tmp_path, monkeypatch):
        rendered = render_hosted_http_base_conf(
            tmp_path,
            monkeypatch,
            {"FEATURE_LISTEN_IP_VERSION": "dual-stack", "FEATURE_PROXY_PROTOCOL": True},
        )
        assert _listen_lines(rendered) == [
            "listen 8080 default_server proxy_protocol;",
            "listen [::]:8080 default_server proxy_protocol;",
        ]
