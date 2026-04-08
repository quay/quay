# -*- coding: utf-8 -*-
"""
Unit tests for organization mirroring model helper functions.
"""

import pytest

from data.model.org_mirror import matches_repository_filter


class TestMatchesRepositoryFilter:
    """Tests for matches_repository_filter function."""

    def test_empty_filters_matches_all(self):
        """Empty filter list should match all repositories."""
        assert matches_repository_filter("any-repo", []) is True
        assert matches_repository_filter("another/repo", []) is True

    def test_none_filters_matches_all(self):
        """None filter list should match all repositories."""
        assert matches_repository_filter("any-repo", None) is True

    def test_exact_match(self):
        """Exact match should work."""
        assert matches_repository_filter("ubuntu", ["ubuntu"]) is True
        assert matches_repository_filter("debian", ["ubuntu"]) is False

    def test_wildcard_suffix(self):
        """Wildcard suffix pattern matching."""
        assert matches_repository_filter("alpine-base", ["alpine*"]) is True
        assert matches_repository_filter("alpine", ["alpine*"]) is True
        assert matches_repository_filter("alpine-3.18", ["alpine*"]) is True
        assert matches_repository_filter("debian", ["alpine*"]) is False

    def test_wildcard_prefix(self):
        """Wildcard prefix pattern matching."""
        assert matches_repository_filter("my-nginx", ["*-nginx"]) is True
        assert matches_repository_filter("nginx", ["*-nginx"]) is False

    def test_wildcard_both(self):
        """Wildcard on both ends."""
        assert matches_repository_filter("app-nginx-proxy", ["*nginx*"]) is True
        assert matches_repository_filter("nginx", ["*nginx*"]) is True
        assert matches_repository_filter("apache", ["*nginx*"]) is False

    def test_question_mark_wildcard(self):
        """Single character wildcard."""
        assert matches_repository_filter("app1", ["app?"]) is True
        assert matches_repository_filter("app2", ["app?"]) is True
        assert matches_repository_filter("app10", ["app?"]) is False
        assert matches_repository_filter("app", ["app?"]) is False

    def test_multiple_filters_any_match(self):
        """Multiple filters - any match should succeed."""
        filters = ["ubuntu", "debian*", "alpine-*"]

        assert matches_repository_filter("ubuntu", filters) is True
        assert matches_repository_filter("debian", filters) is True
        assert matches_repository_filter("debian-11", filters) is True
        assert matches_repository_filter("alpine-3.18", filters) is True
        assert matches_repository_filter("centos", filters) is False

    def test_case_sensitive(self):
        """Matching should be case-sensitive."""
        assert matches_repository_filter("Ubuntu", ["ubuntu"]) is False
        assert matches_repository_filter("ubuntu", ["Ubuntu"]) is False
        assert matches_repository_filter("Ubuntu", ["Ubuntu"]) is True

    def test_character_class(self):
        """Character class patterns."""
        assert matches_repository_filter("app1", ["app[123]"]) is True
        assert matches_repository_filter("app2", ["app[123]"]) is True
        assert matches_repository_filter("app4", ["app[123]"]) is False

    def test_negated_character_class(self):
        """Negated character class patterns."""
        assert matches_repository_filter("app1", ["app[!abc]"]) is True
        assert matches_repository_filter("appa", ["app[!abc]"]) is False
