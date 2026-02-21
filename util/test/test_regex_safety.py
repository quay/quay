import re._parser as re_parser  # type: ignore[import]

import pytest

from data.model import InvalidImmutabilityPolicy
from util.regex_safety import (
    _has_dangerous_nesting,
    _has_overlapping_alternation,
    check_regex_safety,
)


class TestHasDangerousNesting:
    @pytest.mark.parametrize(
        "pattern",
        [
            "(a+)+",
            "(a*)*",
            "(.+)+",
            "([a-z]+)+",
            "(?:a+)+",
            "(a+|b+)+",
            "(a+?)+",
            "((.+)+)",
            "(.+)*",
            "(a+){1,}",
            "(?:.*)+",
            "(\\d+)+",
        ],
        ids=[
            "plus-plus",
            "star-star",
            "dot-plus-plus",
            "class-plus-plus",
            "non-capturing-plus-plus",
            "alternation-plus-plus",
            "lazy-plus-plus",
            "nested-group-dot-plus",
            "dot-plus-star",
            "plus-unbounded-repeat",
            "non-capturing-star-plus",
            "digit-plus-plus",
        ],
    )
    def test_dangerous_patterns_detected(self, pattern):
        parsed = re_parser.parse(pattern)
        assert (
            _has_dangerous_nesting(parsed) is True
        ), f"Expected {pattern!r} to be detected as dangerous"

    @pytest.mark.parametrize(
        "pattern",
        [
            "^v[0-9]+\\.[0-9]+\\.[0-9]+$",
            "^(dev|staging)-.*$",
            "^latest$",
            "a+b+c+",
            "(a{1,10}){1,10}",
            "[a-z]+",
            "^release-[0-9]+$",
            ".*",
            "^v\\d+$",
            "(abc|def)",
        ],
        ids=[
            "semver",
            "alternation-prefix",
            "literal-latest",
            "sequential-quantifiers",
            "both-bounded",
            "simple-class-plus",
            "release-pattern",
            "dot-star",
            "digit-shorthand",
            "simple-alternation",
        ],
    )
    def test_safe_patterns_allowed(self, pattern):
        parsed = re_parser.parse(pattern)
        assert _has_dangerous_nesting(parsed) is False, f"Expected {pattern!r} to be allowed"


class TestHasOverlappingAlternation:
    @pytest.mark.parametrize(
        "pattern",
        [
            "(.|x)+",
            "(\\w|.)+",
            "([^a]|[^b])+",
            "([^a]|x)+",
        ],
        ids=[
            "any-with-literal",
            "category-with-any",
            "not-literal-pair",
            "not-literal-with-literal",
        ],
    )
    def test_dangerous_patterns_detected(self, pattern):
        parsed = re_parser.parse(pattern)
        assert (
            _has_overlapping_alternation(parsed) is True
        ), f"Expected {pattern!r} to be detected as dangerous"

    @pytest.mark.parametrize(
        "pattern",
        [
            "(abc|def)",
            "(a|b)+",
            "^(dev|staging)-.*$",
            "(\\d|[a-z])+",
        ],
        ids=[
            "distinct-literals",
            "non-overlapping-single-chars",
            "alternation-prefix-no-quantifier-wrap",
            "non-overlapping-classes",
        ],
    )
    def test_safe_patterns_allowed(self, pattern):
        parsed = re_parser.parse(pattern)
        assert _has_overlapping_alternation(parsed) is False, f"Expected {pattern!r} to be allowed"


class TestCheckRegexSafety:
    def test_rejects_nested_quantifiers(self):
        with pytest.raises(InvalidImmutabilityPolicy, match="too complex"):
            check_regex_safety("(a+)+")

    def test_rejects_nested_star(self):
        with pytest.raises(InvalidImmutabilityPolicy, match="too complex"):
            check_regex_safety("(.*)*")

    def test_rejects_overlapping_alternation(self):
        with pytest.raises(InvalidImmutabilityPolicy, match="too complex"):
            check_regex_safety("(.|x)+")

    def test_allows_semver(self):
        check_regex_safety("^v[0-9]+\\.[0-9]+\\.[0-9]+$")

    def test_allows_alternation(self):
        check_regex_safety("^(dev|staging)-.*$")

    def test_allows_simple_star(self):
        check_regex_safety(".*")

    def test_invalid_regex_passes_through(self):
        # Invalid regex should not raise from check_regex_safety
        # (the re.compile check in _validate_policy handles that)
        check_regex_safety("[invalid")
