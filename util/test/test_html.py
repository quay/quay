import pytest

from util.html import html2text


@pytest.mark.parametrize(
    "input, expected",
    [
        ("hello world", "hello world"),
        ("hello <strong>world</strong>", "hello *world*"),
        ("<ul><li>foo</li><li>bar</li><li>baz</li></ul>", "* foo\n* bar\n* baz"),
        ("<hr>", ("-" * 80)),
        ('<a href="foo">bar</a>', "[bar](foo)"),
    ],
)
def test_html2text(input, expected):
    assert html2text(input) == expected
