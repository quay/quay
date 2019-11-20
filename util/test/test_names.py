import pytest

from util.names import escape_tag


@pytest.mark.parametrize(
    "input_tag, expected",
    [
        ("latest", "latest"),
        ("latest124", "latest124"),
        ("5de1e98d", "5de1e98d"),
        ("detailed_view#61", "detailed_view_61"),
        ("-detailed_view#61", "_detailed_view_61"),
    ],
)
def test_escape_tag(input_tag, expected):
    assert escape_tag(input_tag) == expected
