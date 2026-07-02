import json
import os
from unittest.mock import patch

import pytest

from config import DefaultConfig
from util.bootstrap_token import (
    DEFAULT_BOOTSTRAP_TOKEN_PATH,
    MAX_BOOTSTRAP_TOKEN_FILE_BYTES,
    delete_bootstrap_token,
    delete_token_file,
    read_bootstrap_token,
    read_token_file,
    write_bootstrap_token,
    write_token_file,
)


def test_default_bootstrap_token_path_matches_config():
    assert DEFAULT_BOOTSTRAP_TOKEN_PATH == DefaultConfig.BOOTSTRAP_TOKEN_PATH


def test_write_token_file_creates_file_with_restrictive_permissions(tmp_path):
    path = str(tmp_path / "token.json")

    write_token_file(path, "mytoken123")

    with open(path) as f:
        assert json.load(f) == {"access_token": "mytoken123"}
    assert os.stat(path).st_mode & 0o777 == 0o600


def test_write_token_file_creates_parents_and_overwrites_existing_file(tmp_path):
    path = str(tmp_path / "a" / "b" / "token.json")

    write_token_file(path, "old")
    write_token_file(path, "new")

    with open(path) as f:
        assert json.load(f) == {"access_token": "new"}
    assert os.stat(tmp_path / "a" / "b").st_mode & 0o777 == 0o700


def test_write_token_file_invalid_path_raises_oserror():
    with pytest.raises(OSError):
        write_token_file("/proc/nonexistent/path/token.json", "tok")


def test_write_token_file_removes_temp_file_on_write_failure(tmp_path):
    path = str(tmp_path / "token.json")

    with patch("util.bootstrap_token.os.write", side_effect=OSError("boom")):
        with pytest.raises(OSError, match="boom"):
            write_token_file(path, "tok")

    assert not os.path.exists(path)
    assert list(tmp_path.glob("*.tmp")) == []


def test_read_token_file_returns_token(tmp_path):
    path = str(tmp_path / "token.json")
    write_token_file(path, "mytoken123")

    assert read_token_file(path) == "mytoken123"


def test_delete_token_file_removes_existing_file(tmp_path):
    path = str(tmp_path / "token.json")
    write_token_file(path, "mytoken123")

    assert delete_token_file(path) is True
    assert not os.path.exists(path)


def test_delete_token_file_missing_file_returns_false(tmp_path):
    path = str(tmp_path / "token.json")

    assert delete_token_file(path) is False


@pytest.mark.parametrize(
    "content",
    [
        None,
        "not-json",
        "{}",
        json.dumps({"access_token": ""}),
        json.dumps({"access_token": None}),
        json.dumps({"access_token": 123}),
        json.dumps(["not", "object"]),
    ],
)
def test_read_token_file_missing_or_malformed_returns_none(tmp_path, content):
    path = tmp_path / "token.json"
    if content is not None:
        path.write_text(content)

    assert read_token_file(str(path)) is None


def test_read_token_file_invalid_utf8_returns_none(tmp_path):
    path = tmp_path / "token.json"
    path.write_bytes(b"\xff\xfe\x00")

    assert read_token_file(str(path)) is None


@pytest.mark.parametrize("error", [IsADirectoryError, PermissionError])
def test_read_token_file_open_os_error_returns_none(error):
    with patch("builtins.open", side_effect=error("boom")):
        assert read_token_file("/unreadable/token.json") is None


def test_read_token_file_oversized_returns_none(tmp_path):
    path = tmp_path / "token.json"
    path.write_text("{" + " " * MAX_BOOTSTRAP_TOKEN_FILE_BYTES + "}")

    assert read_token_file(str(path)) is None


def test_write_and_read_bootstrap_token_uses_configured_path(tmp_path):
    config = {"BOOTSTRAP_TOKEN_PATH": str(tmp_path / "token.json")}

    write_bootstrap_token(config, "mytoken")

    assert read_bootstrap_token(config) == "mytoken"


def test_delete_bootstrap_token_uses_configured_path(tmp_path):
    config = {"BOOTSTRAP_TOKEN_PATH": str(tmp_path / "token.json")}
    write_bootstrap_token(config, "mytoken")

    assert delete_bootstrap_token(config) is True
    assert not os.path.exists(config["BOOTSTRAP_TOKEN_PATH"])


def test_delete_bootstrap_token_missing_file_returns_false(tmp_path):
    config = {"BOOTSTRAP_TOKEN_PATH": str(tmp_path / "token.json")}

    assert delete_bootstrap_token(config) is False
