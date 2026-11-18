import pytest

from config import DefaultConfig, frontend_visible_config


class TestFrontendVisibleConfig:
    def test_branding_passed_through(self):
        config = {
            "BRANDING": {
                "logo": "/static/img/custom.svg",
                "logo_dark": "/static/img/custom-dark.svg",
                "footer_img": "/static/img/footer.svg",
            }
        }
        result = frontend_visible_config(config)
        assert result["BRANDING"]["logo"] == "/static/img/custom.svg"
        assert result["BRANDING"]["logo_dark"] == "/static/img/custom-dark.svg"

    def test_enterprise_logo_url_overrides_branding_logo(self):
        config = {
            "BRANDING": {"logo": "/static/img/original.svg"},
            "ENTERPRISE_LOGO_URL": "/custom/logo.png",
        }
        result = frontend_visible_config(config)
        assert result["BRANDING"]["logo"] == "/custom/logo.png"

    def test_enterprise_logo_url_dark(self):
        config = {
            "BRANDING": {"logo": "/static/img/original.svg"},
            "ENTERPRISE_LOGO_URL": "/custom/logo.png",
            "ENTERPRISE_LOGO_URL_DARK": "/custom/logo-dark.png",
        }
        result = frontend_visible_config(config)
        assert result["BRANDING"]["logo"] == "/custom/logo.png"
        assert result["BRANDING"]["logo_dark"] == "/custom/logo-dark.png"

    def test_enterprise_logo_url_dark_ignored_without_logo_url(self):
        config = {
            "BRANDING": {"logo": "/static/img/original.svg"},
            "ENTERPRISE_LOGO_URL_DARK": "/custom/logo-dark.png",
        }
        result = frontend_visible_config(config)
        assert result["BRANDING"]["logo"] == "/static/img/original.svg"
        assert "logo_dark" not in result["BRANDING"]

    def test_default_branding_has_logo_dark(self):
        assert "logo_dark" in DefaultConfig.BRANDING
        assert DefaultConfig.BRANDING["logo_dark"] is not None

    def test_whitelisted_keys_exclude_secrets(self):
        with pytest.raises(Exception, match="Cannot whitelist secrets"):
            from config import CLIENT_WHITELIST

            CLIENT_WHITELIST.append("SECRET_KEY")
            try:
                frontend_visible_config({"SECRET_KEY": "bad"})
            finally:
                CLIENT_WHITELIST.pop()
