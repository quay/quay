"""Check build-route collisions against the application's registered URL map."""

from unittest.mock import patch
from urllib.parse import urlsplit

import pytest
from werkzeug.exceptions import MethodNotAllowed
from werkzeug.routing import RequestRedirect

from features import FeatureNameValue
from test.fixtures import *  # noqa: F401,F403
from util.names import conflicts_with_build_route


@pytest.mark.parametrize("extended", [False, True])
@pytest.mark.parametrize(
    "name,build_route",
    [
        ("foo/build", True),
        ("foo/build/bar", True),
        ("foo/bar/build/baz", True),
        ("foo/build/bar/status", True),
        ("foo/build/bar/logs", True),
        ("build", False),
        ("build/foo", False),
        ("foo/building/bar", False),
        ("foo/build/bar/extra", False),
        ("foo/bar", False),
    ],
)
@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
def test_registered_build_route_dispatch(app, extended, name, build_route, method):
    with patch(
        "features.EXTENDED_REPOSITORY_NAMES",
        FeatureNameValue("EXTENDED_REPOSITORY_NAMES", extended),
    ):
        adapter = app.url_map.bind("localhost")
        path = "/api/v1/repository/org/" + name
        try:
            endpoint, _ = adapter.match(path, method=method)
        except RequestRedirect as redirect:
            endpoint, _ = adapter.match(urlsplit(redirect.new_url).path, method=method)
            assert name == "foo/build" and method == "GET"
            assert redirect.new_url.endswith("/build/")
        detail_names = {"foo/build/bar", "foo/bar/build/baz"}
        expected_build = build_route and (
            method == "GET" or (method == "DELETE" and name in detail_names)
        )
        assert endpoint.startswith("api.repositorybuild") == expected_build
        if method == "GET":
            assert conflicts_with_build_route(name) is build_route


@pytest.mark.parametrize("extended", [False, True])
@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
def test_build_list_trailing_slash_dispatch(app, extended, method):
    with patch(
        "features.EXTENDED_REPOSITORY_NAMES",
        FeatureNameValue("EXTENDED_REPOSITORY_NAMES", extended),
    ):
        adapter = app.url_map.bind("localhost")
        if method == "GET":
            endpoint, _ = adapter.match("/api/v1/repository/org/foo/build/", method=method)
            assert endpoint.startswith("api.repositorybuild")
        else:
            with pytest.raises(MethodNotAllowed):
                adapter.match("/api/v1/repository/org/foo/build/", method=method)
