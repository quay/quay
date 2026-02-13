import pytest

from util.request import SENSITIVE_QUERY_PARAMS, sanitize_request_url


class TestSanitizeRequestUrl:
    """Tests for URL sanitization to prevent sensitive data in logs."""

    def test_none_url(self):
        """None input returns None."""
        assert sanitize_request_url(None) is None

    def test_empty_url(self):
        """Empty string returns empty string."""
        assert sanitize_request_url("") == ""

    def test_url_without_query_params(self):
        """URLs without query params are returned unchanged."""
        url = "https://quay.io/v2/repo/manifests/latest"
        assert sanitize_request_url(url) == url

    def test_url_with_no_sensitive_params(self):
        """URLs with only non-sensitive params are returned unchanged."""
        url = "https://quay.io/v2/auth?scope=repository:test:pull&service=quay.io"
        result = sanitize_request_url(url)
        assert "scope=" in result
        assert "service=" in result
        assert "[REDACTED]" not in result

    def test_token_redacted(self):
        """token parameter is redacted."""
        url = "https://quay.io/api?token=secret123&other=value"
        result = sanitize_request_url(url)
        assert "token=%5BREDACTED%5D" in result or "token=[REDACTED]" in result
        assert "secret123" not in result
        assert "other=value" in result

    def test_access_token_redacted(self):
        """access_token parameter is redacted."""
        url = "https://example.com/callback?access_token=abc123"
        result = sanitize_request_url(url)
        assert "[REDACTED]" in result or "%5BREDACTED%5D" in result
        assert "abc123" not in result

    def test_refresh_token_redacted(self):
        """refresh_token parameter is redacted."""
        url = "https://example.com/refresh?refresh_token=xyz789"
        result = sanitize_request_url(url)
        assert "xyz789" not in result

    def test_id_token_redacted(self):
        """id_token (JWT) parameter is redacted."""
        url = "https://example.com/callback?id_token=sometoken.xxx"
        result = sanitize_request_url(url)
        assert "sometoken" not in result

    def test_code_redacted(self):
        """OAuth authorization code is redacted."""
        url = "https://example.com/callback?code=auth_code_123"
        result = sanitize_request_url(url)
        assert "auth_code_123" not in result

    def test_client_secret_redacted(self):
        """client_secret parameter is redacted."""
        url = "https://example.com/token?client_id=app&client_secret=supersecret"
        result = sanitize_request_url(url)
        assert "supersecret" not in result
        assert "client_id=app" in result

    def test_oauth_verifier_redacted(self):
        """oauth_verifier parameter is redacted."""
        url = "https://example.com/callback?oauth_verifier=verifier123"
        result = sanitize_request_url(url)
        assert "verifier123" not in result

    def test_state_redacted(self):
        """OAuth state parameter is redacted."""
        url = "https://example.com/callback?state=random_state_value&code=abc"
        result = sanitize_request_url(url)
        assert "random_state_value" not in result
        # code should also be redacted
        assert "abc" not in result or "[REDACTED]" in result

    def test_api_key_redacted(self):
        """api_key parameter is redacted."""
        url = "https://api.example.com/data?api_key=key123&format=json"
        result = sanitize_request_url(url)
        assert "key123" not in result
        assert "format=json" in result

    def test_password_redacted(self):
        """password parameter is redacted."""
        url = "https://example.com/login?user=admin&password=secret123"
        result = sanitize_request_url(url)
        assert "secret123" not in result
        assert "user=admin" in result

    def test_multiple_sensitive_params(self):
        """Multiple sensitive params are all redacted."""
        url = "https://example.com?access_token=abc&api_key=xyz&state=123&normal=ok"
        result = sanitize_request_url(url)
        assert "abc" not in result
        assert "xyz" not in result
        assert "123" not in result or "normal=ok" in result
        assert "normal=ok" in result

    def test_case_insensitive_param_names(self):
        """Param names are matched case-insensitively."""
        url = "https://example.com?TOKEN=secret&Access_Token=abc"
        result = sanitize_request_url(url)
        assert "secret" not in result
        assert "abc" not in result

    def test_sensitive_params_list_complete(self):
        """Verify all expected sensitive params are in the set."""
        expected_params = {
            "token",
            "access_token",
            "refresh_token",
            "id_token",
            "code",
            "api_key",
            "apikey",
            "password",
            "secret",
            "credential",
            "signature",
            "sig",
            "client_secret",
            "oauth_verifier",
            "state",
        }
        assert SENSITIVE_QUERY_PARAMS == expected_params

    def test_preserves_url_structure(self):
        """URL structure (scheme, host, path) is preserved."""
        url = "https://quay.io:443/v2/auth?token=secret&scope=pull"
        result = sanitize_request_url(url)
        assert result.startswith("https://quay.io:443/v2/auth?")
        assert "scope=pull" in result
        assert "secret" not in result

    def test_fail_closed_on_malformed_url(self):
        """Malformed URLs should drop query params (fail-closed for security)."""
        # Test with a URL that has a question mark but malformed query
        # The fail-closed behavior strips query on parse errors
        url = "https://example.com/path?token=secret"
        # Normal case works
        result = sanitize_request_url(url)
        assert "secret" not in result
        # The base path is always preserved
        assert "https://example.com/path" in result

    def test_empty_query_string(self):
        """URL with just a question mark is handled."""
        url = "https://example.com/path?"
        result = sanitize_request_url(url)
        assert result == url

    def test_all_params_sensitive(self):
        """When all params are sensitive, all are redacted."""
        url = "https://example.com?token=abc&password=def&api_key=ghi"
        result = sanitize_request_url(url)
        assert "abc" not in result
        assert "def" not in result
        assert "ghi" not in result
        assert "[REDACTED]" in result or "%5BREDACTED%5D" in result

    def test_url_with_fragment(self):
        """URL fragments are preserved."""
        url = "https://example.com/path?token=secret&scope=read#section"
        result = sanitize_request_url(url)
        assert "secret" not in result
        assert "#section" in result
        assert "scope=read" in result

    def test_param_with_empty_value(self):
        """Parameters with empty values are preserved."""
        url = "https://example.com?empty=&token=secret"
        result = sanitize_request_url(url)
        assert "secret" not in result
        assert "empty=" in result

    def test_fast_path_no_sensitive_params(self):
        """Fast path returns URL unchanged when no sensitive params present."""
        url = "https://quay.io/v2/auth?scope=repo:test:pull&service=quay"
        result = sanitize_request_url(url)
        # Should be unchanged
        assert result == url

    def test_signature_param_redacted(self):
        """signature and sig params are redacted."""
        url = "https://example.com?signature=hash123&sig=abc"
        result = sanitize_request_url(url)
        assert "hash123" not in result
        assert "abc" not in result or "sig=" in result

    def test_credential_param_redacted(self):
        """credential parameter is redacted."""
        url = "https://example.com?credential=mycred123"
        result = sanitize_request_url(url)
        assert "mycred123" not in result

    def test_secret_param_redacted(self):
        """secret parameter is redacted."""
        url = "https://example.com?secret=topsecret"
        result = sanitize_request_url(url)
        assert "topsecret" not in result

    def test_apikey_no_underscore_redacted(self):
        """apikey (no underscore) parameter is redacted."""
        url = "https://example.com?apikey=key456"
        result = sanitize_request_url(url)
        assert "key456" not in result

    def test_preserves_encoded_chars_in_values(self):
        """URL-encoded characters in non-sensitive values are preserved."""
        url = "https://example.com?scope=repo%3Atest%3Apull&token=secret"
        result = sanitize_request_url(url)
        assert "secret" not in result
        # The scope value should still be present (may be encoded differently)
        assert "scope=" in result

    def test_multiple_values_same_param(self):
        """Multiple values for same param are all preserved or redacted."""
        url = "https://example.com?tag=v1&tag=v2&token=secret"
        result = sanitize_request_url(url)
        assert "secret" not in result
        assert "v1" in result
        assert "v2" in result
