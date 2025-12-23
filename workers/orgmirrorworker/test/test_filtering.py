"""
Unit tests for repository filtering logic.

Tests list-based, regex-based, and combined filtering rules.
"""

from unittest.mock import Mock

import pytest

from data.database import RepoMirrorRuleType
from workers.orgmirrorworker.filtering import (
    apply_repo_filters,
    create_combined_rule,
    create_repo_name_list_rule,
    create_repo_name_regex_rule,
    matches_rule,
)

# Test apply_repo_filters


def test_apply_repo_filters_no_rules():
    """Test that no filtering rules allows all repositories."""
    repos = ["repo1", "repo2", "repo3"]

    result = apply_repo_filters(repos, None)

    assert result == repos


def test_apply_repo_filters_empty_repos():
    """Test filtering with empty repository list."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_LIST
    rule.rule_value = {"names": "repo1,repo2"}
    rule.left_child = None
    rule.right_child = None

    result = apply_repo_filters([], rule)

    assert result == []


def test_apply_repo_filters_with_list_rule():
    """Test filtering with list-based rule."""
    repos = ["repo1", "repo2", "repo3", "repo4"]

    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_LIST
    rule.rule_value = {"names": "repo1,repo3"}
    rule.left_child = None
    rule.right_child = None

    result = apply_repo_filters(repos, rule)

    assert result == ["repo1", "repo3"]


def test_apply_repo_filters_with_regex_rule():
    """Test filtering with regex-based rule."""
    repos = ["prod-api", "prod-web", "dev-api", "dev-web"]

    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    rule.rule_value = {"pattern": "^prod-.*"}
    rule.left_child = None
    rule.right_child = None

    result = apply_repo_filters(repos, rule)

    assert result == ["prod-api", "prod-web"]


# Test list-based filtering


def test_list_filter_single_match():
    """Test list filter matching single repository."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_LIST
    rule.rule_value = {"names": "myrepo"}
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("myrepo", rule) is True
    assert matches_rule("other", rule) is False


def test_list_filter_multiple_matches():
    """Test list filter with multiple repository names."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_LIST
    rule.rule_value = {"names": "repo1,repo2,repo3"}
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("repo1", rule) is True
    assert matches_rule("repo2", rule) is True
    assert matches_rule("repo3", rule) is True
    assert matches_rule("repo4", rule) is False


def test_list_filter_no_match():
    """Test list filter with no matching repositories."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_LIST
    rule.rule_value = {"names": "allowed1,allowed2"}
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("notallowed", rule) is False


def test_list_filter_empty_list():
    """Test list filter with empty names list."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_LIST
    rule.rule_value = {"names": ""}
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("anyrepo", rule) is False


def test_list_filter_whitespace():
    """Test list filter handles whitespace in names."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_LIST
    rule.rule_value = {"names": "  repo1  ,  repo2  ,repo3"}
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("repo1", rule) is True
    assert matches_rule("repo2", rule) is True
    assert matches_rule("repo3", rule) is True
    assert matches_rule("  repo1  ", rule) is False  # Exact match, no trim on input


def test_list_filter_case_sensitive():
    """Test list filter is case-sensitive."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_LIST
    rule.rule_value = {"names": "MyRepo"}
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("MyRepo", rule) is True
    assert matches_rule("myrepo", rule) is False
    assert matches_rule("MYREPO", rule) is False


def test_list_filter_missing_names_key():
    """Test list filter with missing 'names' key in rule_value."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_LIST
    rule.rule_value = {"other": "value"}
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("anyrepo", rule) is False


def test_list_filter_null_rule_value():
    """Test list filter with null rule_value."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_LIST
    rule.rule_value = None
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("anyrepo", rule) is False


# Test regex-based filtering


def test_regex_filter_simple_pattern():
    """Test regex filter with simple pattern."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    rule.rule_value = {"pattern": "api"}
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("api", rule) is True
    assert matches_rule("my-api", rule) is True
    assert matches_rule("api-service", rule) is True
    assert matches_rule("web", rule) is False


def test_regex_filter_complex_pattern():
    """Test regex filter with complex pattern (anchors, groups)."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    rule.rule_value = {"pattern": r"^(prod|staging)-[a-z]+$"}
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("prod-api", rule) is True
    assert matches_rule("staging-web", rule) is True
    assert matches_rule("dev-api", rule) is False
    assert matches_rule("prod-api-v2", rule) is False  # Doesn't match $ anchor


def test_regex_filter_no_match():
    """Test regex filter when pattern doesn't match."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    rule.rule_value = {"pattern": "^production-"}
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("development-api", rule) is False
    assert matches_rule("api-production", rule) is False


def test_regex_filter_invalid_pattern():
    """Test regex filter with invalid regex pattern."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    rule.rule_value = {"pattern": "[invalid(pattern"}  # Unclosed bracket
    rule.left_child = None
    rule.right_child = None

    # Invalid patterns should return False (exclude repo)
    assert matches_rule("anyrepo", rule) is False


def test_regex_filter_missing_pattern_key():
    """Test regex filter with missing 'pattern' key in rule_value."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    rule.rule_value = {"other": "value"}
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("anyrepo", rule) is False


def test_regex_filter_null_rule_value():
    """Test regex filter with null rule_value."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    rule.rule_value = None
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("anyrepo", rule) is False


def test_regex_filter_case_sensitive():
    """Test regex filter is case-sensitive by default."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    rule.rule_value = {"pattern": "PROD"}
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("PROD-api", rule) is True
    assert matches_rule("prod-api", rule) is False


def test_regex_filter_partial_match():
    """Test regex filter matches substring."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    rule.rule_value = {"pattern": "api"}
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("my-api-service", rule) is True
    assert matches_rule("api", rule) is True
    assert matches_rule("webapp", rule) is False


def test_regex_filter_multiple_repos():
    """Test regex filter against multiple repository names."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    rule.rule_value = {"pattern": r"^v\d+\.\d+"}
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("v1.0", rule) is True
    assert matches_rule("v2.5-stable", rule) is True
    assert matches_rule("version-1.0", rule) is False
    assert matches_rule("v1", rule) is False


def test_regex_filter_empty_pattern():
    """Test regex filter with empty pattern."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    rule.rule_value = {"pattern": ""}
    rule.left_child = None
    rule.right_child = None

    assert matches_rule("anyrepo", rule) is False


# Test combined rules


def test_combined_and_logic():
    """Test combined rule with AND logic (both must match)."""
    left_rule = Mock()
    left_rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    left_rule.rule_value = {"pattern": "^prod-"}
    left_rule.left_child = None
    left_rule.right_child = None

    right_rule = Mock()
    right_rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    right_rule.rule_value = {"pattern": "-api$"}
    right_rule.left_child = None
    right_rule.right_child = None

    combined = Mock()
    combined.rule_type = RepoMirrorRuleType.REPO_NAME_LIST  # Doesn't matter for internal nodes
    combined.rule_value = {}
    combined.left_child = left_rule
    combined.right_child = right_rule

    assert matches_rule("prod-my-api", combined) is True
    assert matches_rule("prod-web", combined) is False  # Missing -api suffix
    assert matches_rule("dev-my-api", combined) is False  # Missing prod- prefix


def test_combined_one_fails():
    """Test combined rule when one rule fails."""
    left_rule = Mock()
    left_rule.rule_type = RepoMirrorRuleType.REPO_NAME_LIST
    left_rule.rule_value = {"names": "repo1,repo2"}
    left_rule.left_child = None
    left_rule.right_child = None

    right_rule = Mock()
    right_rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    right_rule.rule_value = {"pattern": "^repo"}
    right_rule.left_child = None
    right_rule.right_child = None

    combined = Mock()
    combined.left_child = left_rule
    combined.right_child = right_rule

    assert matches_rule("repo1", combined) is True  # Both match
    assert matches_rule("repo3", combined) is False  # Only regex matches, not in list


def test_nested_rules():
    """Test nested rules (3+ levels)."""
    # Leaf nodes
    rule1 = Mock()
    rule1.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    rule1.rule_value = {"pattern": "^prod-"}
    rule1.left_child = None
    rule1.right_child = None

    rule2 = Mock()
    rule2.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    rule2.rule_value = {"pattern": "-api$"}
    rule2.left_child = None
    rule2.right_child = None

    rule3 = Mock()
    rule3.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    rule3.rule_value = {"pattern": "v[0-9]"}
    rule3.left_child = None
    rule3.right_child = None

    # First level combination
    combined1 = Mock()
    combined1.left_child = rule1
    combined1.right_child = rule2

    # Second level combination
    combined2 = Mock()
    combined2.left_child = combined1
    combined2.right_child = rule3

    # All three must match
    assert matches_rule("prod-v1-api", combined2) is True
    assert matches_rule("prod-api", combined2) is False  # Missing version
    assert matches_rule("prod-v1-web", combined2) is False  # Missing -api suffix


def test_combined_list_and_regex():
    """Test combining list and regex rules."""
    list_rule = Mock()
    list_rule.rule_type = RepoMirrorRuleType.REPO_NAME_LIST
    list_rule.rule_value = {"names": "api-v1,api-v2,web-v1"}
    list_rule.left_child = None
    list_rule.right_child = None

    regex_rule = Mock()
    regex_rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    regex_rule.rule_value = {"pattern": "api"}
    regex_rule.left_child = None
    regex_rule.right_child = None

    combined = Mock()
    combined.left_child = list_rule
    combined.right_child = regex_rule

    assert matches_rule("api-v1", combined) is True  # In list AND matches regex
    assert matches_rule("api-v2", combined) is True  # In list AND matches regex
    assert matches_rule("web-v1", combined) is False  # In list but doesn't match regex
    assert matches_rule("api-v3", combined) is False  # Matches regex but not in list


def test_empty_root_rule():
    """Test that empty root rule returns all repositories."""
    repos = ["repo1", "repo2", "repo3"]

    result = apply_repo_filters(repos, None)

    assert result == repos
    assert len(result) == 3


def test_unknown_rule_type():
    """Test unknown rule type defaults to inclusion."""
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.TAG_GLOB_CSV  # Not applicable to repo filtering
    rule.rule_value = {"glob": "7.6"}
    rule.left_child = None
    rule.right_child = None

    # Should default to include (return True)
    assert matches_rule("anyrepo", rule) is True


# Test performance


def test_filter_1000_repos_list():
    """Test performance of list-based filtering with 1000+ repositories."""
    # Create 1000 repos
    all_repos = [f"repo{i}" for i in range(1000)]

    # Allow first 100
    allowed_names = ",".join([f"repo{i}" for i in range(100)])

    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_LIST
    rule.rule_value = {"names": allowed_names}
    rule.left_child = None
    rule.right_child = None

    result = apply_repo_filters(all_repos, rule)

    assert len(result) == 100
    assert result == [f"repo{i}" for i in range(100)]


def test_filter_1000_repos_regex():
    """Test performance of regex-based filtering with 1000+ repositories."""
    # Create 1000 repos
    all_repos = [f"repo{i}" for i in range(1000)]

    # Match repos 100-199
    rule = Mock()
    rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    rule.rule_value = {"pattern": r"^repo1\d{2}$"}
    rule.left_child = None
    rule.right_child = None

    result = apply_repo_filters(all_repos, rule)

    assert len(result) == 100
    assert result == [f"repo{i}" for i in range(100, 200)]


# Test rule creation helpers


def test_create_repo_name_list_rule(monkeypatch):
    """Test creating a list-based filtering rule."""
    mock_create = Mock(return_value="mock_rule")
    monkeypatch.setattr("workers.orgmirrorworker.filtering.RepoMirrorRule.create", mock_create)

    result = create_repo_name_list_rule("repo1,repo2,repo3")

    mock_create.assert_called_once_with(
        rule_type=RepoMirrorRuleType.REPO_NAME_LIST, rule_value={"names": "repo1,repo2,repo3"}
    )
    assert result == "mock_rule"


def test_create_repo_name_regex_rule(monkeypatch):
    """Test creating a regex-based filtering rule."""
    mock_create = Mock(return_value="mock_rule")
    monkeypatch.setattr("workers.orgmirrorworker.filtering.RepoMirrorRule.create", mock_create)

    result = create_repo_name_regex_rule("^prod-.*")

    mock_create.assert_called_once_with(
        rule_type=RepoMirrorRuleType.REPO_NAME_REGEX, rule_value={"pattern": "^prod-.*"}
    )
    assert result == "mock_rule"


def test_create_regex_rule_invalid_pattern():
    """Test that invalid regex pattern raises ValueError."""
    with pytest.raises(ValueError, match="Invalid regex pattern"):
        create_repo_name_regex_rule("[invalid(pattern")


def test_create_combined_rule(monkeypatch):
    """Test creating a combined rule with children."""
    mock_create = Mock(return_value="mock_combined_rule")
    monkeypatch.setattr("workers.orgmirrorworker.filtering.RepoMirrorRule.create", mock_create)

    left_rule = Mock()
    right_rule = Mock()

    result = create_combined_rule(left_rule, right_rule)

    mock_create.assert_called_once_with(
        rule_type=RepoMirrorRuleType.REPO_NAME_LIST,
        rule_value={},
        left_child=left_rule,
        right_child=right_rule,
    )
    assert result == "mock_combined_rule"


# Integration tests


def test_end_to_end_filtering():
    """Test end-to-end filtering scenario."""
    # Realistic scenario: filter production APIs
    all_repos = [
        "prod-auth-api",
        "prod-user-api",
        "prod-web-frontend",
        "staging-auth-api",
        "staging-user-api",
        "dev-auth-api",
    ]

    # Create rule: starts with "prod-" AND ends with "-api"
    left_rule = Mock()
    left_rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    left_rule.rule_value = {"pattern": "^prod-"}
    left_rule.left_child = None
    left_rule.right_child = None

    right_rule = Mock()
    right_rule.rule_type = RepoMirrorRuleType.REPO_NAME_REGEX
    right_rule.rule_value = {"pattern": "-api$"}
    right_rule.left_child = None
    right_rule.right_child = None

    combined = Mock()
    combined.left_child = left_rule
    combined.right_child = right_rule

    result = apply_repo_filters(all_repos, combined)

    assert result == ["prod-auth-api", "prod-user-api"]
    assert len(result) == 2
