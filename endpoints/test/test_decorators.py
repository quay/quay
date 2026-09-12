from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from data import model
from endpoints.api import api
from endpoints.api.repository import Repository
from endpoints.decorators import check_schema1_push_enabled
from endpoints.test.shared import conduct_call
from image.docker.schema1 import (
    DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE,
)
from test.fixtures import *


@pytest.mark.parametrize(
    "user_agent, include_header, expected_code",
    [
        ("curl/whatever", True, 200),
        ("curl/whatever", False, 200),
        ("Mozilla/whatever", True, 200),
        ("Mozilla/5.0", True, 200),
        (
            "Mozilla/5.0 (Unknown; Linux x86_64) AppleWebKit/534.34 (KHTML, like Gecko) Safari/534.34",
            False,
            400,
        ),
    ],
)
def test_require_xhr_from_browser(user_agent, include_header, expected_code, app, client):
    # Create a public repo with a dot in its name.
    user = model.user.get_user("devtable")
    model.repository.create_repository("devtable", "somerepo.bat", user, "public")

    # Retrieve the repository and ensure we either allow it through or fail, depending on the
    # user agent and header.
    params = {"repository": "devtable/somerepo.bat"}

    headers = {
        "User-Agent": user_agent,
    }

    if include_header:
        headers["X-Requested-With"] = "XMLHttpRequest"

    conduct_call(
        client, Repository, api.url_for, "GET", params, headers=headers, expected_code=expected_code
    )


class AbortCalled(Exception):
    """Exception raised when abort is called, capturing status code and message."""

    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(f"abort({status_code}, {message})")


class TestCheckSchema1PushEnabled:
    """Tests for the check_schema1_push_enabled decorator."""

    @pytest.fixture
    def test_app(self):
        """Create a minimal Flask app for testing the decorator."""
        app = Flask(__name__)
        app.config["V1_PUSH_WHITELIST"] = ["whitelisted_namespace"]
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def mock_abort(self):
        """Create a mock abort function that raises our custom exception."""

        def abort_side_effect(status_code, message=None, **kwargs):
            raise AbortCalled(status_code, message)

        return abort_side_effect

    @pytest.fixture
    def decorated_func(self):
        """Create a simple decorated function for testing."""

        @check_schema1_push_enabled()
        def dummy_endpoint(*args, **kwargs):
            return "success"

        return dummy_endpoint

    @pytest.fixture
    def decorated_func_with_error_class(self):
        """Create a decorated function with custom error class."""

        class CustomError(Exception):
            def __init__(self, detail, http_status_code):
                self.detail = detail
                self.http_status_code = http_status_code

        @check_schema1_push_enabled(error_class=CustomError)
        def dummy_endpoint(*args, **kwargs):
            return "success"

        return dummy_endpoint, CustomError

    def test_allows_push_when_feature_disabled(self, test_app, decorated_func, mock_abort):
        """Push should be allowed when FEATURE_RESTRICTED_V2_SCHEMA1_PUSH is disabled."""
        with test_app.test_request_context("/", content_type=DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE):
            with patch("endpoints.decorators.features") as mock_features:
                with patch("endpoints.decorators.abort", mock_abort):
                    mock_features.RESTRICTED_V2_SCHEMA1_PUSH = False

                    result = decorated_func(namespace_name="any_namespace")
                    assert result == "success"

    def test_allows_push_when_namespace_whitelisted(self, test_app, decorated_func, mock_abort):
        """Push should be allowed when namespace is in whitelist."""
        with test_app.test_request_context("/", content_type=DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE):
            with patch("endpoints.decorators.features") as mock_features:
                with patch("endpoints.decorators.app", test_app):
                    with patch("endpoints.decorators.abort", mock_abort):
                        mock_features.RESTRICTED_V2_SCHEMA1_PUSH = True

                        result = decorated_func(namespace_name="whitelisted_namespace")
                        assert result == "success"

    @pytest.mark.parametrize(
        "content_type",
        [
            DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE,
            DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE,
            None,
            "application/json",
        ],
    )
    def test_blocks_schema1_push_when_not_whitelisted(
        self, test_app, decorated_func, content_type, mock_abort
    ):
        """Schema1 push should be blocked when namespace is not in whitelist."""
        with test_app.test_request_context("/", content_type=content_type):
            with patch("endpoints.decorators.features") as mock_features:
                with patch("endpoints.decorators.app", test_app):
                    with patch("endpoints.decorators.abort", mock_abort):
                        mock_features.RESTRICTED_V2_SCHEMA1_PUSH = True

                        with pytest.raises(AbortCalled) as exc_info:
                            decorated_func(namespace_name="blocked_namespace")

                        assert exc_info.value.status_code == 405

    @pytest.mark.parametrize(
        "content_type",
        [
            "application/vnd.docker.distribution.manifest.v2+json",
            "application/vnd.oci.image.manifest.v1+json",
            "application/vnd.docker.distribution.manifest.list.v2+json",
            "application/vnd.oci.image.index.v1+json",
        ],
    )
    def test_allows_non_schema1_push_when_not_whitelisted(
        self, test_app, decorated_func, content_type, mock_abort
    ):
        """Non-schema1 push should be allowed even when namespace is not whitelisted."""
        with test_app.test_request_context("/", content_type=content_type):
            with patch("endpoints.decorators.features") as mock_features:
                with patch("endpoints.decorators.app", test_app):
                    with patch("endpoints.decorators.abort", mock_abort):
                        mock_features.RESTRICTED_V2_SCHEMA1_PUSH = True

                        result = decorated_func(namespace_name="blocked_namespace")
                        assert result == "success"

    def test_raises_custom_error_class_when_provided(
        self, test_app, decorated_func_with_error_class, mock_abort
    ):
        """Should raise custom error class when provided."""
        decorated_func, CustomError = decorated_func_with_error_class

        with test_app.test_request_context("/", content_type=DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE):
            with patch("endpoints.decorators.features") as mock_features:
                with patch("endpoints.decorators.app", test_app):
                    with patch("endpoints.decorators.abort", mock_abort):
                        mock_features.RESTRICTED_V2_SCHEMA1_PUSH = True

                        with pytest.raises(CustomError) as exc_info:
                            decorated_func(namespace_name="blocked_namespace")

                        assert exc_info.value.http_status_code == 405
                        assert "disabled" in exc_info.value.detail["message"]

    def test_blocks_push_when_whitelist_empty(self, test_app, decorated_func, mock_abort):
        """Push should be blocked when whitelist is empty (not None)."""
        test_app.config["V1_PUSH_WHITELIST"] = []

        with test_app.test_request_context("/", content_type=DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE):
            with patch("endpoints.decorators.features") as mock_features:
                with patch("endpoints.decorators.app", test_app):
                    with patch("endpoints.decorators.abort", mock_abort):
                        mock_features.RESTRICTED_V2_SCHEMA1_PUSH = True

                        with pytest.raises(AbortCalled) as exc_info:
                            decorated_func(namespace_name="any_namespace")

                        assert exc_info.value.status_code == 405

    def test_blocks_push_when_whitelist_not_configured(self, test_app, decorated_func, mock_abort):
        """Push should be blocked when whitelist is not configured (None)."""
        test_app.config["V1_PUSH_WHITELIST"] = None

        with test_app.test_request_context("/", content_type=DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE):
            with patch("endpoints.decorators.features") as mock_features:
                with patch("endpoints.decorators.app", test_app):
                    with patch("endpoints.decorators.abort", mock_abort):
                        mock_features.RESTRICTED_V2_SCHEMA1_PUSH = True

                        with pytest.raises(AbortCalled) as exc_info:
                            decorated_func(namespace_name="any_namespace")

                        assert exc_info.value.status_code == 405
