from unittest.mock import MagicMock, patch

import pytest

from auth import scopes
from endpoints.api import require_robot_api_access, require_scope
from endpoints.exception import Unauthorized
from test.fixtures import *


def test_require_robot_api_access_rejects_unscoped_robot(app):
    with (
        app.app_context(),
        patch(
            "endpoints.api.get_authenticated_context",
            return_value=MagicMock(robot=MagicMock(), robot_scopes=None),
        ),
    ):
        protected = require_robot_api_access(lambda: "ok")

        with pytest.raises(Unauthorized):
            protected()


def test_require_scope_rejects_unscoped_robot(app):
    with (
        app.app_context(),
        patch(
            "endpoints.api.get_authenticated_context",
            return_value=MagicMock(robot=MagicMock(), robot_scopes=None),
        ),
    ):
        protected = require_scope(scopes.READ_REPO)(lambda: "ok")

        with pytest.raises(Unauthorized):
            protected()


def test_require_scope_allows_robot_with_matching_scope(app):
    with (
        app.app_context(),
        patch(
            "endpoints.api.get_authenticated_context",
            return_value=MagicMock(robot=MagicMock(), robot_scopes="repo:read"),
        ),
    ):
        protected = require_scope(scopes.READ_REPO)(lambda: "ok")

        assert protected() == "ok"


def test_require_scope_does_not_restrict_nonrobot_context(app):
    with (
        app.app_context(),
        patch(
            "endpoints.api.get_authenticated_context",
            return_value=MagicMock(spec=["robot"], robot=None),
        ),
    ):
        protected = require_scope(scopes.READ_REPO)(lambda: "ok")

        assert protected() == "ok"
