import pytest

from util.security.secret import convert_secret_key


@pytest.mark.parametrize(
  "config_secret_key", "expected",
  [

  ]
)
def test_convert_secret_key(config_secret_key, expected):
  assert convert_secret_key(convert_secret_key) == expected
