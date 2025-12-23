"""
Repository filtering logic for organization mirrors.

Provides list-based and regex-based filtering of repository names using
the existing RepoMirrorRule tree infrastructure.
"""

import logging
import re

from data.database import RepoMirrorRule, RepoMirrorRuleType

logger = logging.getLogger(__name__)


def apply_repo_filters(repo_names, root_rule):
    """
    Apply filtering rules to repository names.

    Args:
        repo_names: List of repository names from discovery
        root_rule: RepoMirrorRule (root of rule tree) or None

    Returns:
        List of filtered repository names
    """
    if not root_rule:
        # No filtering - return all repositories
        logger.debug("No filtering rules configured, allowing all %d repositories", len(repo_names))
        return repo_names

    if not repo_names:
        logger.debug("No repositories to filter")
        return []

    filtered = [name for name in repo_names if matches_rule(name, root_rule)]

    logger.info("Filtered %d repositories to %d using rule tree", len(repo_names), len(filtered))

    return filtered


def matches_rule(repo_name, rule):
    """
    Check if a repository name matches a filtering rule.

    Supports tree-based rules with AND/OR logic:
    - If rule has children: recursively evaluate
    - If rule is a leaf: apply specific rule type

    Args:
        repo_name: Repository name to test
        rule: RepoMirrorRule

    Returns:
        True if matches, False otherwise
    """
    if rule.left_child and rule.right_child:
        # Internal node - combine children with AND logic
        left_match = matches_rule(repo_name, rule.left_child)
        right_match = matches_rule(repo_name, rule.right_child)
        return left_match and right_match

    # Leaf node - apply specific rule type
    if rule.rule_type == RepoMirrorRuleType.REPO_NAME_LIST:
        return _matches_name_list(repo_name, rule.rule_value)
    elif rule.rule_type == RepoMirrorRuleType.REPO_NAME_REGEX:
        return _matches_regex(repo_name, rule.rule_value)
    else:
        # Unknown rule type or tag-based rule (not applicable to repo filtering)
        logger.warning(
            "Rule type %s not applicable to repository filtering, defaulting to include",
            rule.rule_type,
        )
        return True  # Default to include


def _matches_name_list(repo_name, rule_value):
    """
    Check if repository name is in comma-separated list.

    Args:
        repo_name: Repository name
        rule_value: Dict with "names" key containing comma-separated list

    Returns:
        True if name is in list
    """
    if not rule_value or "names" not in rule_value:
        logger.warning("Invalid rule_value for REPO_NAME_LIST: %s", rule_value)
        return False

    names_csv = rule_value["names"]
    if not names_csv:
        logger.warning("Empty names list in REPO_NAME_LIST rule")
        return False

    allowed_names = [name.strip() for name in names_csv.split(",")]

    return repo_name in allowed_names


def _matches_regex(repo_name, rule_value):
    """
    Check if repository name matches regex pattern.

    Args:
        repo_name: Repository name
        rule_value: Dict with "pattern" key containing regex pattern

    Returns:
        True if matches pattern, False if invalid pattern or no match
    """
    if not rule_value or "pattern" not in rule_value:
        logger.warning("Invalid rule_value for REPO_NAME_REGEX: %s", rule_value)
        return False

    pattern = rule_value["pattern"]
    if not pattern:
        logger.warning("Empty pattern in REPO_NAME_REGEX rule")
        return False

    try:
        regex = re.compile(pattern)
        return regex.search(repo_name) is not None
    except re.error as e:
        logger.error(
            "Invalid regex pattern '%s': %s. Excluding repository '%s'.",
            pattern,
            str(e),
            repo_name,
        )
        return False  # Invalid pattern - exclude repo


def create_repo_name_list_rule(names_csv):
    """
    Create a list-based filtering rule.

    Args:
        names_csv: Comma-separated list of repository names

    Returns:
        RepoMirrorRule
    """
    return RepoMirrorRule.create(
        rule_type=RepoMirrorRuleType.REPO_NAME_LIST, rule_value={"names": names_csv}
    )


def create_repo_name_regex_rule(pattern):
    """
    Create a regex-based filtering rule.

    Args:
        pattern: Regular expression pattern

    Returns:
        RepoMirrorRule

    Raises:
        ValueError: If pattern is invalid
    """
    # Validate pattern
    try:
        re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {str(e)}")

    return RepoMirrorRule.create(
        rule_type=RepoMirrorRuleType.REPO_NAME_REGEX, rule_value={"pattern": pattern}
    )


def create_combined_rule(left_rule, right_rule):
    """
    Create a combined rule (AND logic).

    Args:
        left_rule: RepoMirrorRule
        right_rule: RepoMirrorRule

    Returns:
        RepoMirrorRule with left and right children
    """
    # Use REPO_NAME_LIST as parent type (doesn't matter for internal nodes)
    return RepoMirrorRule.create(
        rule_type=RepoMirrorRuleType.REPO_NAME_LIST,
        rule_value={},
        left_child=left_rule,
        right_child=right_rule,
    )
