import pytest

from auth.scopes import (
    scopes_from_scope_string,
    validate_scope_string,
    ALL_SCOPES,
    is_subset_string,
)


@pytest.mark.parametrize(
    "scopes_string, expected",
    [
        # Valid single scopes.
        ("repo:read", ["repo:read"]),
        ("repo:admin", ["repo:admin"]),
        # Invalid scopes.
        ("not:valid", []),
        ("repo:admins", []),
        # Valid scope strings.
        ("repo:read repo:admin", ["repo:read", "repo:admin"]),
        ("repo:read,repo:admin", ["repo:read", "repo:admin"]),
        ("repo:read,repo:admin repo:write", ["repo:read", "repo:admin", "repo:write"]),
        # Partially invalid scopes.
        ("repo:read,not:valid", []),
        ("repo:read repo:admins", []),
        # Invalid scope strings.
        ("repo:read|repo:admin", []),
        # Mixture of delimiters.
        ("repo:read, repo:admin", []),
    ],
)
def test_parsing(scopes_string, expected):
    expected_scope_set = {ALL_SCOPES[scope_name] for scope_name in expected}
    parsed_scope_set = scopes_from_scope_string(scopes_string)
    assert parsed_scope_set == expected_scope_set
    assert validate_scope_string(scopes_string) == bool(expected)


@pytest.mark.parametrize(
    "superset, subset, result",
    [
        ("repo:read", "repo:read", True),
        ("repo:read repo:admin", "repo:read", True),
        ("repo:read,repo:admin", "repo:read", True),
        ("repo:read,repo:admin", "repo:admin", True),
        ("repo:read,repo:admin", "repo:admin repo:read", True),
        ("", "repo:read", False),
        ("unknown:tag", "repo:read", False),
        ("repo:read unknown:tag", "repo:read", False),
        ("repo:read,unknown:tag", "repo:read", False),
    ],
)
def test_subset_string(superset, subset, result):
    assert is_subset_string(superset, subset) == result
