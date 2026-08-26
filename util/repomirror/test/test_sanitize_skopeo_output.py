from util.repomirror.skopeomirror import sanitize_skopeo_output


class TestSanitizeSkopeoOutput:
    def test_none_passthrough(self):
        assert sanitize_skopeo_output(None) is None

    def test_empty_string_passthrough(self):
        assert sanitize_skopeo_output("") == ""

    def test_normal_error_unchanged(self):
        msg = 'time="2024-01-01" level=fatal msg="manifest unknown"'
        assert sanitize_skopeo_output(msg) == msg

    def test_authorization_basic_redacted(self):
        line = "Authorization: Basic dXNlcjpwYXNz"
        assert sanitize_skopeo_output(line) == "Authorization: [REDACTED]"

    def test_authorization_bearer_redacted(self):
        line = "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
        assert sanitize_skopeo_output(line) == "Authorization: [REDACTED]"

    def test_authorization_case_insensitive(self):
        line = "authorization: basic dXNlcjpwYXNz"
        assert sanitize_skopeo_output(line) == "authorization: [REDACTED]"

    def test_src_creds_equals_redacted(self):
        line = "--src-creds=user:password123"
        assert sanitize_skopeo_output(line) == "--src-creds=[REDACTED]"

    def test_dest_creds_space_redacted(self):
        line = "--dest-creds user:password123"
        assert sanitize_skopeo_output(line) == "--dest-creds [REDACTED]"

    def test_creds_equals_redacted(self):
        line = "--creds=user:password123"
        assert sanitize_skopeo_output(line) == "--creds=[REDACTED]"

    def test_auth_json_field_redacted(self):
        line = '{"auth": "dXNlcjpwYXNzd29yZA=="}'
        assert sanitize_skopeo_output(line) == '{"auth": "[REDACTED]"}'

    def test_multiline_mixed_content(self):
        output = (
            'time="2024-01-01" level=debug msg="GET /v2/"\n'
            "Authorization: Bearer eyJtoken123\n"
            'time="2024-01-01" level=fatal msg="manifest unknown"\n'
        )
        result = sanitize_skopeo_output(output)
        assert "eyJtoken123" not in result
        assert "Authorization: [REDACTED]" in result
        assert 'msg="manifest unknown"' in result

    def test_error_context_preserved(self):
        output = (
            "FATA[0002] Error reading manifest latest in registry.example.com/repo: "
            "manifest unknown: manifest unknown"
        )
        assert sanitize_skopeo_output(output) == output
