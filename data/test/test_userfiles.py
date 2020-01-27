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

    rv = client.open("/mockuserfiles/foo/bar/baz", method="GET")
    assert rv.status_code == 404
