import pytest

from config_app.config_util.tar import tarinfo_filter_partial

from util.config.validator import EXTRA_CA_DIRECTORY

from test.fixtures import *


class MockTarInfo:
    def __init__(self, name, isdir):
        self.name = name
        self.isdir = lambda: isdir

    def __eq__(self, other):
        return other is not None and self.name == other.name


@pytest.mark.parametrize(
    "prefix,tarinfo,expected",
    [
        # It should handle simple files
        (
            "Users/sam/",
            MockTarInfo("Users/sam/config.yaml", False),
            MockTarInfo("config.yaml", False),
        ),
        # It should allow the extra CA dir
        (
            "Users/sam/",
            MockTarInfo("Users/sam/%s" % EXTRA_CA_DIRECTORY, True),
            MockTarInfo("%s" % EXTRA_CA_DIRECTORY, True),
        ),
        # it should allow a file in that extra dir
        (
            "Users/sam/",
            MockTarInfo("Users/sam/%s/cert.crt" % EXTRA_CA_DIRECTORY, False),
            MockTarInfo("%s/cert.crt" % EXTRA_CA_DIRECTORY, False),
        ),
        # it should not allow a directory that isn't the CA dir
        ("Users/sam/", MockTarInfo("Users/sam/dirignore", True), None),
    ],
)
def test_tarinfo_filter(prefix, tarinfo, expected):
    partial = tarinfo_filter_partial(prefix)
    assert partial(tarinfo) == expected
