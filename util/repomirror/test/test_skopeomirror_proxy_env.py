# -*- coding: utf-8 -*-
"""Skopeo proxy env: explicit mirror mapping vs process environment."""

import os
from unittest.mock import patch

import pytest

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

    def test_setup_env_does_not_inherit_ambient_when_explicit_empty(self):
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

    def test_ssrf_validator_uses_explicit_proxy_not_ambient_env(self):
        from util.security.ssrf import ProxyRoute, proxy_route_for_url

        explicit = {"https_proxy": "http://explicit:8443"}
        with patch.dict(os.environ, {"HTTPS_PROXY": "http://ambient:9999"}, clear=False):
            assert proxy_route_for_url("https://registry.example.com", explicit) is ProxyRoute.PROXY
            assert proxy_route_for_url("https://registry.example.com", None) is ProxyRoute.DIRECT
