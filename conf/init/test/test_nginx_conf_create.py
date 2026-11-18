import json
import os
import re
import shutil
from pathlib import Path

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
        blob_upload_client_body_timeout=None,
        blob_upload_lingering_close=None,
        blob_upload_lingering_time=None,
        blob_upload_lingering_timeout=None,
        enable_alb_health_check=False,
        secscan_enabled=True,
        secscan_notifications_enabled=True,
        proxy_cache_enabled=True,
    )
    defaults.update(kwargs)
    return template.render(**defaults)


def _sts_token_location(rendered):
    return re.search(r"location = /sts/token \{([^}]*)\}", rendered, re.DOTALL).group(1)


def _secscan_location(rendered):
    return re.search(r"location (?:\^~ )?/secscan/\s*\{[^}]*\}", rendered, re.DOTALL).group(0)


def _upstream_proxy_location(rendered):
    return re.search(r"location ~ \^/_upstream_proxy/[^{]*\{([^}]*)\}", rendered, re.DOTALL).group(
        0
    )


def _secscan_notifications_location_present(rendered):
    match = re.search(r"location = /secscan/notification \{([^}]*)\}", rendered, re.DOTALL)
    if match:
        return match.group(0)
    else:
        return None


def test_sts_token_is_routed_to_web_app():
    location = _sts_token_location(render_server_base_conf())
    assert "proxy_pass http://web_app_server;" in location


def test_sts_token_uses_nginx_rate_limits_when_enabled():
    rendered = render_server_base_conf(enable_rate_limits=True)
    location = _sts_token_location(rendered)
    assert "limit_req zone=dynamicauth_heavy_http1 burst=5 nodelay;" in location
    assert "limit_req zone=dynamicauth_heavy_http2 burst=25 nodelay;" in location
    assert "error_page 429 = @sts_rate_limited;" in location
    assert "location @sts_rate_limited {" in rendered
    assert "add_header Retry-After 1 always;" in rendered
    assert 'return 429 \'{"error":"slow_down"}\';' in rendered


def test_sts_token_omits_nginx_rate_limits_when_disabled():
    rendered = render_server_base_conf(enable_rate_limits=False)
    location = _sts_token_location(rendered)
    assert "limit_req" not in location
    assert "@sts_rate_limited" not in rendered


class TestSecscanLocationDirective:
    def test_secscan_points_to_secscan_server_when_secscan_enabled_true(self):
        """
        Verifies that with default configuration secscan points to secscan_app_server.
        """
        rendered = render_server_base_conf()
        match = _secscan_location(rendered)
        assert match is not None
        assert "proxy_pass http://secscan_app_server;" in match

    def test_secscan_returns_404_when_secscan_enabled_false(self):
        """
        Verifies that when secscan is turned off, the endpoint points to web_app_server.
        """
        rendered = render_server_base_conf(secscan_enabled=False)
        match = _secscan_location(rendered)
        assert match is not None
        assert "return 404;" in match
        assert "proxy_pass" not in match

    def test_secscan_notification_is_not_present_in_generated_config(self):
        """
        Verifies that /secscan/notification is not present in the config if secscan and
        security notifications are enabled.
        """
        rendered = render_server_base_conf()
        match = _secscan_notifications_location_present(rendered)
        assert match is None

    def test_sescan_notification_is_not_present_in_generated_config_if_secscan_is_disabled(self):
        """
        Verifies that /secscan/notification is not present in the config if secscan is disabled.
        """
        rendered = render_server_base_conf(secscan_enabled=False)
        match = _secscan_notifications_location_present(rendered)
        assert match is None

    def test_secscan_notification_is_present_in_generated_config_if_notifications_are_disabled(
        self,
    ):
        """
        Verifies that /secscan/notification is present in the config if secscan is enabled, but
        security notifications are disabled and that it returns a 404.
        """
        rendered = render_server_base_conf(secscan_notifications_enabled=False)
        match = _secscan_notifications_location_present(rendered)
        assert match is not None
        assert "return 404;" in match


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


def _blob_location(rendered):
    match = re.search(
        r"location ~ /v2/\(\[.*?\]\+\)\(/\[.*?\]\+\)\+/blobs/ \{(.*?)\n\}",
        rendered,
        re.DOTALL,
    )
    assert match is not None, "blob location block not found in rendered config"
    return match.group(1)


class TestBlobUploadClientBodyTimeout:
    def test_omits_client_body_timeout_when_unset(self):
        rendered = render_server_base_conf()
        blob_block = _blob_location(rendered)
        assert "client_body_timeout" not in blob_block

    def test_omits_client_body_timeout_when_none(self):
        rendered = render_server_base_conf(blob_upload_client_body_timeout=None)
        blob_block = _blob_location(rendered)
        assert "client_body_timeout" not in blob_block

    @pytest.mark.parametrize("value", ["3600", "120", "60", "2000"])
    def test_renders_client_body_timeout_when_set(self, value):
        rendered = render_server_base_conf(blob_upload_client_body_timeout=value)
        blob_block = _blob_location(rendered)
        assert f"client_body_timeout {value};" in blob_block

    def test_proxy_read_timeout_remains_hardcoded(self):
        rendered = render_server_base_conf(blob_upload_client_body_timeout="3600")
        blob_block = _blob_location(rendered)
        assert "proxy_read_timeout 2000;" in blob_block

    def test_omits_lingering_directives_when_unset(self):
        rendered = render_server_base_conf()
        blob_block = _blob_location(rendered)
        assert "lingering_close" not in blob_block
        assert "lingering_time" not in blob_block
        assert "lingering_timeout" not in blob_block

    def test_renders_lingering_close_when_set(self):
        rendered = render_server_base_conf(blob_upload_lingering_close="always")
        blob_block = _blob_location(rendered)
        assert "lingering_close always;" in blob_block

    def test_renders_lingering_time_when_set(self):
        rendered = render_server_base_conf(blob_upload_lingering_time="60")
        blob_block = _blob_location(rendered)
        assert "lingering_time 60;" in blob_block

    def test_renders_lingering_timeout_when_set(self):
        rendered = render_server_base_conf(blob_upload_lingering_timeout="30")
        blob_block = _blob_location(rendered)
        assert "lingering_timeout 30;" in blob_block


def _alb_location(rendered):
    match = re.search(r"location = /health/alb \{(.*?)\n\}", rendered, re.DOTALL)
    return match.group(1) if match else None


class TestAlbHealthCheck:
    def test_omitted_when_disabled(self):
        assert _alb_location(render_server_base_conf(enable_alb_health_check=False)) is None

    def test_rendered_when_enabled(self):
        block = _alb_location(render_server_base_conf(enable_alb_health_check=True))
        assert block is not None
        assert "if (-f /tmp/quay-drain) {" in block
        assert "return 503;" in block
        assert "proxy_pass http://web_app_server/_internal_ping;" in block


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


def render_server_base_conf_through_nginx_conf_create(tmp_path, monkeypatch, config, env=None):
    """
    Similarly to render_server_base_conf, it creates the new server-base.conf file, but
    utilizes a full nginx-create path to do so instead of manipulating the Jinja template directly.
    """
    nginx_path = os.path.join(tmp_path, "nginx")
    os.mkdir(nginx_path)

    shutil.copy(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../../nginx/server-base.conf.jnj",
        ),
        nginx_path,
    )

    monkeypatch.setattr(nginx_conf_create, "QUAYCONF_DIR", str(tmp_path))
    monkeypatch.delenv("QUAY_OVERRIDE_CONFIG", raising=False)
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)

    nginx_conf_create.generate_server_config(config)
    return Path(nginx_path, "server-base.conf").read_text(encoding="utf-8")


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


class TestServerBaseConfCreation:
    @pytest.mark.parametrize(
        ("config", "env", "state"),
        [
            pytest.param(
                {"FEATURE_SECURITY_SCANNER": True, "FEATURE_SECURITY_NOTIFICATIONS": True},
                None,
                "enabled",
                id="scanner-and-notifications-on",
            ),
            pytest.param(
                {"FEATURE_SECURITY_SCANNER": True, "FEATURE_SECURITY_NOTIFICATIONS": False},
                None,
                "notifications-blocked",
                id="scanner-on-notifications-off",
            ),
            pytest.param(
                {"FEATURE_SECURITY_SCANNER": False, "FEATURE_SECURITY_NOTIFICATIONS": True},
                None,
                "disabled",
                id="scanner-off-notifications-on",
            ),
            pytest.param(
                {},
                None,
                "disabled",
                id="empty-config",
            ),
            pytest.param(
                None,
                None,
                "disabled",
                id="config-not-provided",
            ),
            pytest.param(
                {
                    "FEATURE_SECURITY_SCANNER": True,
                    "FEATURE_SECURITY_NOTIFICATIONS": True,
                    "ACCOUNT_RECOVERY_MODE": True,
                },
                None,
                "disabled",
                id="both-on-but-account-recovery-mode-set",
            ),
            pytest.param(
                {},
                {
                    "QUAY_OVERRIDE_CONFIG": json.dumps({}),
                },
                "disabled",
                id="empty-quay-override-provided",
            ),
            pytest.param(
                {},
                {
                    "QUAY_OVERRIDE_CONFIG": json.dumps(
                        {"FEATURE_SECURITY_SCANNER": True, "FEATURE_SECURITY_NOTIFICATIONS": True},
                    ),
                },
                "enabled",
                id="scanner-and-notifier-turned-on-through-override",
            ),
            pytest.param(
                {},
                {
                    "QUAY_OVERRIDE_CONFIG": json.dumps(
                        {"FEATURE_SECURITY_SCANNER": True, "FEATURE_SECURITY_NOTIFICATIONS": False},
                    ),
                },
                "notifications-blocked",
                id="scanner-on-notifications-off-via-quay-override",
            ),
            pytest.param(
                {},
                {
                    "QUAY_OVERRIDE_CONFIG": "{this is not a valid json",
                },
                "enabled",
                id="wrong-json-override",
            ),
            pytest.param(
                {},
                {
                    "QUAY_OVERRIDE_CONFIG": json.dumps("{this is not a valid json"),
                },
                "enabled",
                id="override-is-json-string-not-object",
            ),
        ],
    )
    def test_config_rendering(self, tmp_path, monkeypatch, config, env, state):
        """
        Verifies that the correct server-base.conf is created with provided parameters.
        """
        # the combination of secscan and secscan_notifications can yield three different states.
        # based on the enabled workers, these states need to be verified against the
        # generated configuration.
        EXPECTED = {
            "disabled": ("return 404;", False),
            "notifications-blocked": ("proxy_pass http://secscan_app_server;", True),
            "enabled": ("proxy_pass http://secscan_app_server;", False),
        }

        rendered = render_server_base_conf_through_nginx_conf_create(
            tmp_path, monkeypatch, config, env
        )
        prefix_expected, notifications_blocked = EXPECTED[state]

        exact = re.search(r"location = /secscan \{([^}]*)\}", rendered, re.DOTALL)
        prefix = _secscan_location(rendered)
        assert prefix_expected in prefix

        if state == "disabled":
            assert "proxy_pass" not in prefix
            assert exact is not None and "return 404;" in exact.group(0)
        else:
            assert "proxy_pass" in prefix
            assert "return 404;" not in prefix
            assert exact is None

        assert (
            _secscan_notifications_location_present(rendered) is not None
        ) == notifications_blocked
        assert "{%" not in rendered and "{ %" not in rendered

    @pytest.mark.parametrize(
        ("config", "env", "expected"),
        [
            pytest.param(
                {"FEATURE_PROXY_CACHE": True},
                None,
                True,
                id="proxy-cache-enabled",
            ),
            pytest.param(
                {"FEATURE_PROXY_CACHE": False},
                None,
                False,
                id="proxy-cache-disabled",
            ),
            pytest.param(
                {},
                None,
                False,
                id="empty-config-and-no-overrides",
            ),
            pytest.param(
                None,
                None,
                False,
                id="no-config-provided-and-no-overrides",
            ),
            pytest.param(
                {},
                {
                    "QUAY_OVERRIDE_CONFIG": json.dumps({"FEATURE_PROXY_CACHE": True}),
                },
                True,
                id="proxy-cache-enabled-through-override",
            ),
            pytest.param(
                {"FEATURE_PROXY_CACHE": True, "ACCOUNT_RECOVERY_MODE": True},
                {},
                False,
                id="proxy-cache-enabled-account-recovery-mode-enabled",
            ),
            pytest.param(
                {},
                {"QUAY_OVERRIDE_CONFIG": "{this is not a valid json"},
                True,
                id="invalid-override-enables-proxy-cache",
            ),
        ],
    )
    def test_upstream_proxy_rendering(self, tmp_path, monkeypatch, config, env, expected):
        """
        Verifies that the _upstream_proxy endpoint is properly rendered based on
        feature flags and command line overrides.
        """
        rendered = render_server_base_conf_through_nginx_conf_create(
            tmp_path, monkeypatch, config, env
        )
        location = _upstream_proxy_location(rendered)

        if expected:
            assert "proxy_pass http://blobstream_app_server;" in location
            assert "return 404;" not in location
        else:
            assert "proxy_pass http://blobstream_app_server;" not in location
            assert "return 404;" in location

        # we cannot have multiple _upstream_proxy definitions
        num_locations = re.findall(r"location ~ \^/_upstream_proxy/", rendered)
        assert len(num_locations) == 1
