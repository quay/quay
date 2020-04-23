import base64
import pytest

from flask import url_for

from data import model
from endpoints.appr.registry import appr_bp, blobs
from endpoints.test.shared import client_with_identity
from test.fixtures import *

BLOB_ARGS = {"digest": "abcd1235"}
PACKAGE_ARGS = {"release": "r", "media_type": "foo"}
RELEASE_ARGS = {"release": "r"}
CHANNEL_ARGS = {"channel_name": "c"}
CHANNEL_RELEASE_ARGS = {"channel_name": "c", "release": "r"}


@pytest.mark.parametrize(
    "resource,method,params,owned_by,is_public,identity,expected",
    [
        ("appr.blobs", "GET", BLOB_ARGS, "devtable", False, "public", 403),
        ("appr.blobs", "GET", BLOB_ARGS, "devtable", False, "devtable", 404),
        ("appr.blobs", "GET", BLOB_ARGS, "devtable", True, "public", 404),
        ("appr.blobs", "GET", BLOB_ARGS, "devtable", True, "devtable", 404),
        ("appr.delete_package", "DELETE", PACKAGE_ARGS, "devtable", False, "public", 403),
        ("appr.delete_package", "DELETE", PACKAGE_ARGS, "devtable", False, "devtable", 404),
        ("appr.delete_package", "DELETE", PACKAGE_ARGS, "devtable", True, "public", 403),
        ("appr.delete_package", "DELETE", PACKAGE_ARGS, "devtable", True, "devtable", 404),
        ("appr.show_package", "GET", PACKAGE_ARGS, "devtable", False, "public", 403),
        ("appr.show_package", "GET", PACKAGE_ARGS, "devtable", False, "devtable", 404),
        ("appr.show_package", "GET", PACKAGE_ARGS, "devtable", True, "public", 404),
        ("appr.show_package", "GET", PACKAGE_ARGS, "devtable", True, "devtable", 404),
        ("appr.show_package_releases", "GET", {}, "devtable", False, "public", 403),
        ("appr.show_package_releases", "GET", {}, "devtable", False, "devtable", 200),
        ("appr.show_package_releases", "GET", {}, "devtable", True, "public", 200),
        ("appr.show_package_releases", "GET", {}, "devtable", True, "devtable", 200),
        (
            "appr.show_package_release_manifests",
            "GET",
            RELEASE_ARGS,
            "devtable",
            False,
            "public",
            403,
        ),
        (
            "appr.show_package_release_manifests",
            "GET",
            RELEASE_ARGS,
            "devtable",
            False,
            "devtable",
            200,
        ),
        (
            "appr.show_package_release_manifests",
            "GET",
            RELEASE_ARGS,
            "devtable",
            True,
            "public",
            200,
        ),
        (
            "appr.show_package_release_manifests",
            "GET",
            RELEASE_ARGS,
            "devtable",
            True,
            "devtable",
            200,
        ),
        ("appr.pull", "GET", PACKAGE_ARGS, "devtable", False, "public", 403),
        ("appr.pull", "GET", PACKAGE_ARGS, "devtable", False, "devtable", 404),
        ("appr.pull", "GET", PACKAGE_ARGS, "devtable", True, "public", 404),
        ("appr.pull", "GET", PACKAGE_ARGS, "devtable", True, "devtable", 404),
        ("appr.push", "POST", {}, "devtable", False, "public", 403),
        ("appr.push", "POST", {}, "devtable", False, "devtable", 400),
        ("appr.push", "POST", {}, "devtable", True, "public", 403),
        ("appr.push", "POST", {}, "devtable", True, "devtable", 400),
        ("appr.list_channels", "GET", {}, "devtable", False, "public", 403),
        ("appr.list_channels", "GET", {}, "devtable", False, "devtable", 200),
        ("appr.list_channels", "GET", {}, "devtable", True, "public", 200),
        ("appr.list_channels", "GET", {}, "devtable", True, "devtable", 200),
        ("appr.show_channel", "GET", CHANNEL_ARGS, "devtable", False, "public", 403),
        ("appr.show_channel", "GET", CHANNEL_ARGS, "devtable", False, "devtable", 404),
        ("appr.show_channel", "GET", CHANNEL_ARGS, "devtable", True, "public", 404),
        ("appr.show_channel", "GET", CHANNEL_ARGS, "devtable", True, "devtable", 404),
        ("appr.delete_channel", "DELETE", CHANNEL_ARGS, "devtable", False, "public", 403),
        ("appr.delete_channel", "DELETE", CHANNEL_ARGS, "devtable", False, "devtable", 404),
        ("appr.delete_channel", "DELETE", CHANNEL_ARGS, "devtable", True, "public", 403),
        ("appr.delete_channel", "DELETE", CHANNEL_ARGS, "devtable", True, "devtable", 404),
        (
            "appr.add_channel_release",
            "POST",
            CHANNEL_RELEASE_ARGS,
            "devtable",
            False,
            "public",
            403,
        ),
        (
            "appr.add_channel_release",
            "POST",
            CHANNEL_RELEASE_ARGS,
            "devtable",
            False,
            "devtable",
            404,
        ),
        ("appr.add_channel_release", "POST", CHANNEL_RELEASE_ARGS, "devtable", True, "public", 403),
        (
            "appr.add_channel_release",
            "POST",
            CHANNEL_RELEASE_ARGS,
            "devtable",
            True,
            "devtable",
            404,
        ),
        (
            "appr.delete_channel_release",
            "DELETE",
            CHANNEL_RELEASE_ARGS,
            "devtable",
            False,
            "public",
            403,
        ),
        (
            "appr.delete_channel_release",
            "DELETE",
            CHANNEL_RELEASE_ARGS,
            "devtable",
            False,
            "devtable",
            404,
        ),
        (
            "appr.delete_channel_release",
            "DELETE",
            CHANNEL_RELEASE_ARGS,
            "devtable",
            True,
            "public",
            403,
        ),
        (
            "appr.delete_channel_release",
            "DELETE",
            CHANNEL_RELEASE_ARGS,
            "devtable",
            True,
            "devtable",
            404,
        ),
    ],
)
def test_api_security(
    resource, method, params, owned_by, is_public, identity, expected, app, client
):
    app.register_blueprint(appr_bp, url_prefix="/cnr")

    with client_with_identity(identity, client) as cl:
        owner = model.user.get_user(owned_by)
        visibility = "public" if is_public else "private"
        model.repository.create_repository(
            owned_by, "someapprepo", owner, visibility=visibility, repo_kind="application"
        )

        params["namespace"] = owned_by
        params["package_name"] = "someapprepo"
        params["_csrf_token"] = "123csrfforme"

        url = url_for(resource, **params)
        headers = {}
        if identity is not None:
            auth = base64.b64encode(("%s:password" % identity).encode("ascii"))
            headers["authorization"] = "basic " + auth.decode("ascii")

        rv = cl.open(url, headers=headers, method=method)
        assert rv.status_code == expected
