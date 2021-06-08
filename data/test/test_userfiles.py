import pytest

from mock import Mock
from io import BytesIO

from data.userfiles import DelegateUserfiles, Userfiles
from test.fixtures import *


@pytest.mark.parametrize(
    "prefix,path,expected",
    [
        ("test", "foo", "test/foo"),
        ("test", "bar", "test/bar"),
        ("test", "/bar", "test/bar"),
        ("test", "../foo", "test/foo"),
        ("test", "foo/bar/baz", "test/baz"),
        ("test", "foo/../baz", "test/baz"),
        (None, "foo", "foo"),
        (None, "foo/bar/baz", "baz"),
    ],
)
def test_filepath(prefix, path, expected):
    userfiles = DelegateUserfiles(None, None, "local_us", prefix)
    assert userfiles.get_file_id_path(path) == expected


def test_lookup_userfile(app, client):
    uuid = "deadbeef-dead-beef-dead-beefdeadbeef"
    bad_uuid = "deadduck-dead-duck-dead-duckdeadduck"
    upper_uuid = "DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF"

    def _stream_read_file(locations, path):
        if path.find(uuid) > 0 or path.find(upper_uuid) > 0:
            return BytesIO(b"hello world")

        raise IOError("Not found!")

    storage_mock = Mock()
    storage_mock.stream_read_file = _stream_read_file

    app.config["USERFILES_PATH"] = "foo"
    Userfiles(
        app, distributed_storage=storage_mock, path="mockuserfiles", handler_name="mockuserfiles"
    )

    rv = client.open("/mockuserfiles/" + uuid, method="GET")
    assert rv.status_code == 200

    rv = client.open("/mockuserfiles/" + upper_uuid, method="GET")
    assert rv.status_code == 200

    rv = client.open("/mockuserfiles/" + bad_uuid, method="GET")
    assert rv.status_code == 404

    # NOTE: With the changes to the path converter for the extended repository names regex,
    # this route conflicts with one of the route using the <reponame> regex.
    # i.e /mockuserfiles/foo/bar/baz would match another url route.
    # In order to 404 on this path, The Userfiles' path would need the full
    # /mockuserfiles/foo/bar as a path for the Flask url_rule.
    rv = client.open("/mockuserfiles/foo/bar/baz", method="GET")
    # assert rv.status_code == 404
    assert rv.status_code == 308


def test_lookup_userfile_with_nested_path(app, client):
    uuid = "deadbeef-dead-beef-dead-beefdeadbeef"
    bad_uuid = "deadduck-dead-duck-dead-duckdeadduck"
    upper_uuid = "DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF"

    def _stream_read_file(locations, path):
        if path.find(uuid) > 0 or path.find(upper_uuid) > 0:
            return BytesIO(b"hello world")

        raise IOError("Not found!")

    storage_mock = Mock()
    storage_mock.stream_read_file = _stream_read_file

    Userfiles(
        app,
        distributed_storage=storage_mock,
        path="mockuserfiles/foo/bar",
        handler_name="mockuserfiles2",
    )

    rv = client.open("/mockuserfiles/foo/bar/" + uuid, method="GET")
    assert rv.status_code == 200

    rv = client.open("/mockuserfiles/foo/bar/" + upper_uuid, method="GET")
    assert rv.status_code == 200

    rv = client.open("/mockuserfiles/foo/bar/" + bad_uuid, method="GET")
    assert rv.status_code == 404

    rv = client.open("/mockuserfiles/foo/bar/baz", method="GET")
    assert rv.status_code == 404

    # The follwing path should conflict with the reponame regex
    rv = client.open("/mockuserfiles/" + uuid, method="GET")
    assert rv.status_code == 308

    rv = client.open("/mockuserfiles/" + upper_uuid, method="GET")
    assert rv.status_code == 308

    rv = client.open("/mockuserfiles/" + bad_uuid, method="GET")
    assert rv.status_code == 308
