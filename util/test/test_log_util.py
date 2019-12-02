import pytest
import os
from util.log import logfile_path, filter_logs
from app import FILTERED_VALUES
from _init import CONF_DIR


def test_filter_logs():
    values = {
        "user": {"password": "toto"},
        "blob": "1234567890asdfewkqresfdsfewfdsfd",
        "unfiltered": "foo",
    }
    filter_logs(values, FILTERED_VALUES)
    assert values == {"user": {"password": "[FILTERED]"}, "blob": "12345678", "unfiltered": "foo"}


@pytest.mark.parametrize(
    "debug,jsonfmt,expected",
    [
        (False, False, os.path.join(CONF_DIR, "logging.conf")),
        (False, True, os.path.join(CONF_DIR, "logging_json.conf")),
        (True, False, os.path.join(CONF_DIR, "logging_debug.conf")),
        (True, True, os.path.join(CONF_DIR, "logging_debug_json.conf")),
    ],
)
def test_logfile_path(debug, jsonfmt, expected, monkeypatch):
    assert logfile_path(jsonfmt=jsonfmt, debug=debug) == expected


@pytest.mark.parametrize(
    "debug,jsonfmt,expected",
    [
        ("false", "false", os.path.join(CONF_DIR, "logging.conf")),
        ("false", "true", os.path.join(CONF_DIR, "logging_json.conf")),
        ("true", "false", os.path.join(CONF_DIR, "logging_debug.conf")),
        ("true", "true", os.path.join(CONF_DIR, "logging_debug_json.conf")),
    ],
)
def test_logfile_path_env(debug, jsonfmt, expected, monkeypatch):
    monkeypatch.setenv("DEBUGLOG", debug)
    monkeypatch.setenv("JSONLOG", jsonfmt)
    assert logfile_path() == expected


def test_logfile_path_default():
    assert logfile_path() == os.path.join(CONF_DIR, "logging.conf")
