import os
import re

import pytest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")

EXTERNAL_CDN_DOMAINS = [
    "fonts.googleapis.com",
    "netdna.bootstrapcdn.com",
    "maxcdn.bootstrapcdn.com",
]

EXTERNAL_CDN_PATTERN = re.compile(
    r'(?:href|src)\s*=\s*["\'](?:https?:)?//(?:'
    + "|".join(re.escape(d) for d in EXTERNAL_CDN_DOMAINS)
    + r")",
    re.IGNORECASE,
)

JINJA_TEMPLATES = [
    "templates/generatedtoken.html",
    "templates/message.html",
    "templates/error.html",
]

STATIC_PAGES = [
    "static/502.html",
]


class TestNoHardcodedCDN:
    @pytest.mark.parametrize("template_path", JINJA_TEMPLATES + STATIC_PAGES)
    def test_no_hardcoded_external_cdn_urls(self, template_path):
        filepath = os.path.join(REPO_ROOT, template_path)
        with open(filepath) as f:
            content = f.read()

        matches = EXTERNAL_CDN_PATTERN.findall(content)
        assert not matches, (
            f"{template_path} contains hardcoded external CDN references: {matches}. "
            f"Jinja templates should use the external_styles variable instead. "
            f"Static pages should use inline CSS. (PROJQUAY-11235)"
        )

    @pytest.mark.parametrize("template_path", JINJA_TEMPLATES)
    def test_jinja_templates_use_external_styles_variable(self, template_path):
        filepath = os.path.join(REPO_ROOT, template_path)
        with open(filepath) as f:
            content = f.read()

        assert "external_styles" in content, (
            f"{template_path} does not reference the external_styles template variable. "
            f"Templates rendered via render_page_template must use external_styles "
            f"to respect the USE_CDN config flag. (PROJQUAY-11235)"
        )

    def test_502_has_no_external_dependencies(self):
        filepath = os.path.join(REPO_ROOT, "static/502.html")
        with open(filepath) as f:
            content = f.read()

        protocol_relative = re.findall(r'(?:href|src)\s*=\s*["\'](?:https?:)?//', content)
        assert not protocol_relative, (
            f"static/502.html contains external resource references: {protocol_relative}. "
            f"This file is served by nginx as a static page and cannot use Jinja variables. "
            f"All styling must be inline. (PROJQUAY-11235)"
        )


try:
    from test.fixtures import *

    _has_fixtures = True
except ImportError:
    _has_fixtures = False


@pytest.mark.skipif(not _has_fixtures, reason="test.fixtures unavailable (missing Flask deps)")
class TestTemplateRendering:
    @pytest.mark.parametrize(
        "template_name",
        [
            "generatedtoken.html",
            "message.html",
        ],
    )
    def test_template_renders_with_local_styles(self, template_name, app):
        from flask import render_template

        local_styles = [
            "/static/ldn/font-awesome.css-abc123",
            "/static/ldn/bootstrap.min.css-def456",
        ]

        config_set = {
            "BRANDING": {"logo": "/static/img/quay_logo.png"},
        }

        with app.app_context():
            html = render_template(
                template_name,
                external_styles=local_styles,
                config_set=config_set,
                onprem=True,
                message="Test message",
            )

        for style_url in local_styles:
            assert style_url in html, f"{template_name} did not render local style URL {style_url}"

        for domain in EXTERNAL_CDN_DOMAINS:
            assert (
                domain not in html
            ), f"{template_name} rendered with hardcoded CDN domain {domain}"

    def test_error_template_renders_with_local_styles(self, app):
        from flask import render_template

        local_styles = [
            "/static/ldn/font-awesome.css-abc123",
            "/static/ldn/bootstrap.min.css-def456",
        ]

        config_set = {
            "BRANDING": {
                "logo": "/static/img/quay_logo.png",
            },
        }

        with app.app_context():
            html = render_template(
                "500.html",
                external_styles=local_styles,
                config_set=config_set,
                onprem=True,
                has_billing=False,
            )

        for style_url in local_styles:
            assert (
                style_url in html
            ), f"500.html (extends error.html) did not render local style URL {style_url}"

        for domain in EXTERNAL_CDN_DOMAINS:
            assert (
                domain not in html
            ), f"500.html (extends error.html) rendered with hardcoded CDN domain {domain}"
