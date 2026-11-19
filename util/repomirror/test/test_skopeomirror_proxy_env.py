# -*- coding: utf-8 -*-
"""Skopeo proxy env: explicit mirror mapping vs process environment."""

import os
from unittest.mock import patch

from util.repomirror.skopeomirror import SkopeoMirror


class TestSkopeoMirrorProxyEnv:
    def test_setup_env_applies_explicit_proxy_only(self):
        mirror = SkopeoMirror()
        with patch.dict(
            os.environ,
            {"HTTP_PROXY": "http://ambient:9999", "HTTPS_PROXY": "http://ambient:9999"},
            clear=False,
        ):
            env = mirror.setup_env(
                {
                    "http_proxy": "http://explicit:8080",
                    "https_proxy": "http://explicit:8443",
                }
            )
        assert env["HTTP_PROXY"] == "http://explicit:8080"
        assert env["HTTPS_PROXY"] == "http://explicit:8443"

    def test_setup_env_falls_back_to_ambient_when_explicit_empty(self):
        mirror = SkopeoMirror()
        with patch.dict(
            os.environ,
            {"HTTP_PROXY": "http://ambient:9999", "HTTPS_PROXY": "http://ambient:9999"},
            clear=False,
        ):
            env = mirror.setup_env({"http_proxy": "", "https_proxy": "", "no_proxy": ""})
        assert env["HTTP_PROXY"] == "http://ambient:9999"
        assert env["HTTPS_PROXY"] == "http://ambient:9999"

    def test_run_skopeo_passes_explicit_proxy_env(self):
        mirror = SkopeoMirror()
        captured_env = {}

        def fake_popen(args, shell, stdout, stderr, env):
            captured_env.update(env)

            class _Proc:
                returncode = 0

                def wait(self, timeout=None):
                    return 0

            return _Proc()

        with patch("util.repomirror.skopeomirror.subprocess.Popen", side_effect=fake_popen):
            mirror.run_skopeo(
                ["skopeo", "version"],
                {
                    "http_proxy": "http://explicit:8080",
                    "https_proxy": "http://explicit:8443",
                    "no_proxy": "localhost",
                },
                timeout=30,
            )

        assert captured_env["HTTP_PROXY"] == "http://explicit:8080"
        assert captured_env["HTTPS_PROXY"] == "http://explicit:8443"
        assert captured_env["NO_PROXY"] == "localhost"

    def test_setup_env_preserves_ambient_no_proxy_when_no_explicit_proxy(self):
        mirror = SkopeoMirror()
        with patch.dict(
            os.environ,
            {
                "HTTP_PROXY": "http://ambient:9999",
                "HTTPS_PROXY": "http://ambient:9999",
                "NO_PROXY": "ambient.local",
            },
            clear=False,
        ):
            env = mirror.setup_env({})
        assert env["HTTP_PROXY"] == "http://ambient:9999"
        assert env["HTTPS_PROXY"] == "http://ambient:9999"
        assert env["NO_PROXY"] == "ambient.local"

    def test_setup_env_clears_ambient_no_proxy_when_explicit_proxy_omits_no_proxy(self):
        """Explicit proxy without no_proxy must agree with proxy_route_for_url (PROXY)."""
        from util.security.ssrf import ProxyRoute, proxy_route_for_url

        mirror = SkopeoMirror()
        explicit = {
            "http_proxy": "http://explicit:8080",
            "https_proxy": "http://explicit:8443",
        }
        with patch.dict(
            os.environ,
            {
                "HTTP_PROXY": "http://ambient:9999",
                "HTTPS_PROXY": "http://ambient:9999",
                "NO_PROXY": "registry.example.com",
            },
            clear=False,
        ):
            env = mirror.setup_env(explicit)

        assert env["HTTP_PROXY"] == "http://explicit:8080"
        assert env["HTTPS_PROXY"] == "http://explicit:8443"
        assert "NO_PROXY" not in env
        assert "no_proxy" not in env
        assert proxy_route_for_url("https://registry.example.com", explicit) is ProxyRoute.PROXY

    def test_setup_env_applies_explicit_all_proxy(self):
        """Explicit all_proxy must reach Skopeo so SSRF PROXY routing is not stranded."""
        from util.security.ssrf import ProxyRoute, proxy_route_for_url

        mirror = SkopeoMirror()
        explicit = {"all_proxy": "http://all-proxy:8080"}
        with patch.dict(os.environ, {}, clear=True):
            env = mirror.setup_env(explicit)

        assert env["HTTP_PROXY"] == "http://all-proxy:8080"
        assert env["HTTPS_PROXY"] == "http://all-proxy:8080"
        assert env["ALL_PROXY"] == "http://all-proxy:8080"
        assert proxy_route_for_url("https://registry.example.com", explicit) is ProxyRoute.PROXY

    def test_setup_env_scheme_proxy_wins_over_all_proxy(self):
        mirror = SkopeoMirror()
        with patch.dict(os.environ, {}, clear=True):
            env = mirror.setup_env(
                {
                    "https_proxy": "http://https-proxy:8443",
                    "all_proxy": "http://all-proxy:8080",
                }
            )
        assert env["HTTPS_PROXY"] == "http://https-proxy:8443"
        assert env["HTTP_PROXY"] == "http://all-proxy:8080"
        assert env["ALL_PROXY"] == "http://all-proxy:8080"

    def test_setup_env_http_proxy_wins_https_falls_back_to_all_proxy(self):
        mirror = SkopeoMirror()
        with patch.dict(os.environ, {}, clear=True):
            env = mirror.setup_env(
                {
                    "http_proxy": "http://http-proxy:8080",
                    "all_proxy": "http://all-proxy:8080",
                }
            )
        assert env["HTTP_PROXY"] == "http://http-proxy:8080"
        assert env["HTTPS_PROXY"] == "http://all-proxy:8080"
        assert env["ALL_PROXY"] == "http://all-proxy:8080"

    def test_setup_env_explicit_empty_no_proxy_clears_ambient(self):
        """Explicit proxy with empty no_proxy must clear ambient NO_PROXY."""
        mirror = SkopeoMirror()
        with patch.dict(
            os.environ,
            {
                "HTTP_PROXY": "http://ambient:9999",
                "HTTPS_PROXY": "http://ambient:9999",
                "NO_PROXY": "registry.example.com",
            },
            clear=True,
        ):
            env = mirror.setup_env(
                {
                    "http_proxy": "http://explicit:8080",
                    "https_proxy": "http://explicit:8443",
                    "no_proxy": "",
                }
            )
        assert env["HTTP_PROXY"] == "http://explicit:8080"
        assert env["HTTPS_PROXY"] == "http://explicit:8443"
        assert "NO_PROXY" not in env
        assert "no_proxy" not in env

    def test_setup_env_no_proxy_only_keeps_ambient_proxy(self):
        mirror = SkopeoMirror()
        with patch.dict(
            os.environ,
            {"HTTPS_PROXY": "http://ambient:9999", "NO_PROXY": "other.example.com"},
            clear=True,
        ):
            env = mirror.setup_env({"no_proxy": "registry.example.com"})
        assert env["HTTPS_PROXY"] == "http://ambient:9999"
        assert env["NO_PROXY"] == "registry.example.com"

    def test_setup_env_materializes_ambient_all_proxy_into_scheme_vars(self):
        """Go ignores ALL_PROXY; empty mirror proxy must still reach HTTP(S)_PROXY."""
        mirror = SkopeoMirror()
        with patch.dict(os.environ, {"ALL_PROXY": "http://all-proxy:8080"}, clear=True):
            env = mirror.setup_env({})
        assert env["ALL_PROXY"] == "http://all-proxy:8080"
        assert env["HTTP_PROXY"] == "http://all-proxy:8080"
        assert env["HTTPS_PROXY"] == "http://all-proxy:8080"

    def test_ssrf_validator_uses_explicit_proxy_not_ambient_env(self):
        from util.security.ssrf import ProxyRoute, proxy_route_for_url

        explicit = {"https_proxy": "http://explicit:8443"}
        with patch.dict(os.environ, {"HTTPS_PROXY": "http://ambient:9999"}, clear=False):
            assert proxy_route_for_url("https://registry.example.com", explicit) is ProxyRoute.PROXY
            assert proxy_route_for_url("https://registry.example.com", None) is ProxyRoute.DIRECT
