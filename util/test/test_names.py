# -*- coding: utf-8 -*-

import pytest
import re

from util.names import escape_tag, REPOSITORY_NAME_REGEX, REPOSITORY_NAME_EXTENDED_REGEX


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


@pytest.mark.parametrize(
    "name, extended_name, should_match",
    [
        ("devtable", False, True),  # Lowercase allowed
        ("DevTable", False, False),  # Uppercase NOT allowed
        ("dev-table", False, True),  # Hyphens allowed
        ("dev_table", False, True),  # Underscores allowed
        ("devtable123", False, True),  # Numbers allowed
        ("🌸", False, False),  # Non-ASCII NOT allowed
        (".foo", False, False),  # Cannot start with a dot
        ("_foo", False, False),  # Cannot start with an underscore
        ("-foo", False, False),  # Cannot start with a dash
        ("a" * 255, False, True),  # Up to 255 characters allowed
        ("b" * 256, False, False),  # 256 or more characters not allowed
        # Names with path components
        ("devtable/path/to/repo", True, True),  # Lowercase allowed
        ("DevTable/path/to/RePo", True, False),  # Upercase not allowed
        ("devtable/path/to/repo-name", True, True),  # Hyphens allowed
        ("devtable/path_to/repo/name", True, True),  # Underscores allowed
        ("devtable/path/to/repo123", True, True),  # Numbers allowed
        ("devtable/path/to/repo🌸name", True, False),  # Non-ASCII NOT allowed
        ("devtable/path/to/.reponame", True, False),  # Path component cannot start with a dot
        ("devtable/path/-to/reponame", True, False),  # Path component cannot start with a dash
        (
            "devtable/_path/to/reponame",
            True,
            False,
        ),  # Path component cannot start with an underscore
        ("devtable/_path/to/reponame/", True, False),  # Trailing slash not allowed
        ("/devtable/path/to/reponame", True, False),  # Leading slash not allowed
        ("devtable/path/to//reponame", True, False),  # Multiple consecutive slashes not allowed
        ("1/2/3" * 51, True, True),  # Up to 255 characters allowed
        ("1/2/3/78" * 32, True, False),  # # 256 or more characters not allowed
    ],
)
def test_repository_names_regex(name, extended_name, should_match):
    """
    Verify that repository names conform to the standards/specifications.
    """
    result = re.match(REPOSITORY_NAME_REGEX, name)
    result_extended = re.match(REPOSITORY_NAME_EXTENDED_REGEX, name)

    if not extended_name:
        assert bool(result) == should_match and bool(result_extended) == should_match
    else:
        assert bool(result_extended) == should_match
