import pytest

from util.config.provider import FileConfigProvider

from test.fixtures import *


class TestFileConfigProvider(FileConfigProvider):
    def __init__(self):
        self.yaml_filename = "yaml_filename"
        self._service_token = "service_token"
        self.config_volume = "config_volume"
        self.py_filename = "py_filename"
        self.yaml_path = os.path.join(self.config_volume, self.yaml_filename)
        self.py_path = os.path.join(self.config_volume, self.py_filename)


@pytest.mark.parametrize(
    "directory,filename,expected",
    [
        ("directory", "file", "directory/file"),
        ("directory/dir", "file", "directory/dir/file"),
        ("directory/dir/", "file", "directory/dir/file"),
        ("directory", "file/test", "directory/file/test"),
    ],
)
def test_get_volume_path(directory, filename, expected):
    provider = TestFileConfigProvider()

    assert expected == provider.get_volume_path(directory, filename)
