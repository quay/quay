"""
Regex safety utilities to prevent ReDoS (Regular Expression Denial of Service).

Two-layer static defense:
1. Nested quantifier detection - detects nested unbounded quantifiers at pattern creation time
2. Overlapping alternation detection - detects alternation branches inside unbounded
   quantifiers where branches can match the same character (causes exponential backtracking)
"""

import logging
import re
import re._parser as re_parser  # type: ignore[import]

from data.model import InvalidImmutabilityPolicy

logger = logging.getLogger(__name__)

_QUANTIFIER_OPS = (re_parser.MAX_REPEAT, re_parser.MIN_REPEAT)

_REJECTION_MESSAGE = "Regex pattern rejected: pattern is too complex. Please simplify the pattern."


def _is_unbounded(max_count) -> bool:
    """Check if a quantifier's max count is unbounded (MAXREPEAT)."""
    return max_count == re_parser.MAXREPEAT


def _has_dangerous_nesting(parsed_pattern) -> bool:
    """
    Walk the re._parser AST to detect quantifiers nested inside other quantifiers
    where at least one is unbounded. This pattern causes catastrophic backtracking.

    Each AST node is a tuple of (op, args). Quantifier nodes (MAX_REPEAT, MIN_REPEAT)
    have args = (min, max, subpattern). SUBPATTERN nodes have args = (group, add_flags,
    del_flags, subpattern). BRANCH nodes have args = (None, [branch1, branch2, ...]).
    """

    def _walk(items, inside_unbounded_quantifier: bool) -> bool:
        for op, av in items:
            if op in _QUANTIFIER_OPS:
                _min_count, max_count, subpattern = av
                this_is_unbounded = _is_unbounded(max_count)

                if inside_unbounded_quantifier and this_is_unbounded:
                    return True

                if _walk(subpattern, inside_unbounded_quantifier or this_is_unbounded):
                    return True

            elif op == re_parser.SUBPATTERN:
                _group, _add_flags, _del_flags, subpattern = av
                if _walk(subpattern, inside_unbounded_quantifier):
                    return True

            elif op == re_parser.BRANCH:
                _unused, branches = av
                for branch in branches:
                    if _walk(branch, inside_unbounded_quantifier):
                        return True

        return False

    return _walk(parsed_pattern.data, False)


def _first_matchable(branch):
    """
    Extract the first matchable element from an AST branch.

    Returns a tuple (op, av) of the first element that actually matches a character,
    skipping anchors and other zero-width assertions. Returns None if the branch
    is empty or contains only zero-width elements.
    """
    _ZERO_WIDTH_OPS = {
        re_parser.AT,
        re_parser.ASSERT,
        re_parser.ASSERT_NOT,
        re_parser.AT_BEGINNING,
        re_parser.AT_END,
    }

    for op, av in branch:
        if op in _ZERO_WIDTH_OPS:
            continue
        if op == re_parser.SUBPATTERN:
            _group, _add_flags, _del_flags, subpattern = av
            result = _first_matchable(subpattern)
            if result is not None:
                return result
            continue
        return (op, av)
    return None


def _elements_overlap(a, b) -> bool:
    """
    Conservatively check if two AST elements can match the same character.

    Returns True if overlap is possible (may have false positives for safety).
    """
    op_a, av_a = a
    op_b, av_b = b

    # ANY (dot) overlaps with everything
    if op_a == re_parser.ANY or op_b == re_parser.ANY:
        return True

    # NOT_LITERAL overlaps with almost everything (conservative)
    if op_a == re_parser.NOT_LITERAL or op_b == re_parser.NOT_LITERAL:
        return True

    # Two identical literals
    if op_a == re_parser.LITERAL and op_b == re_parser.LITERAL:
        return av_a == av_b

    # Two IN (character class) or CATEGORY nodes — conservative overlap
    if op_a in (re_parser.IN, re_parser.CATEGORY) and op_b in (re_parser.IN, re_parser.CATEGORY):
        return True

    # LITERAL vs IN/CATEGORY — conservative overlap
    if (op_a == re_parser.LITERAL and op_b in (re_parser.IN, re_parser.CATEGORY)) or (
        op_b == re_parser.LITERAL and op_a in (re_parser.IN, re_parser.CATEGORY)
    ):
        return True

    return False


def _has_overlapping_alternation(parsed_pattern) -> bool:
    """
    Walk the AST looking for BRANCH nodes inside unbounded quantifiers where
    two or more branches can match the same first character.

    This detects patterns like (a|a)+, (\\d|\\w)+, (.|x)+ which cause
    exponential backtracking.
    """

    def _walk(items, inside_unbounded_quantifier: bool) -> bool:
        for op, av in items:
            if op in _QUANTIFIER_OPS:
                _min_count, max_count, subpattern = av
                this_is_unbounded = _is_unbounded(max_count)
                if _walk(subpattern, inside_unbounded_quantifier or this_is_unbounded):
                    return True

            elif op == re_parser.SUBPATTERN:
                _group, _add_flags, _del_flags, subpattern = av
                if _walk(subpattern, inside_unbounded_quantifier):
                    return True

            elif op == re_parser.BRANCH:
                _unused, branches = av

                # Recurse into each branch
                for branch in branches:
                    if _walk(branch, inside_unbounded_quantifier):
                        return True

                # Check for overlapping first-matchable elements between branches
                if inside_unbounded_quantifier:
                    first_elements = []
                    for branch in branches:
                        elem = _first_matchable(branch)
                        if elem is not None:
                            first_elements.append(elem)

                    # Pairwise overlap check
                    for i in range(len(first_elements)):
                        for j in range(i + 1, len(first_elements)):
                            if _elements_overlap(first_elements[i], first_elements[j]):
                                return True

        return False

    return _walk(parsed_pattern.data, False)


def check_regex_safety(pattern: str) -> None:
    """
    Check if a regex pattern is safe from ReDoS attacks.

    Raises InvalidImmutabilityPolicy if the pattern is dangerous.

    Layer 1: Static AST analysis for nested unbounded quantifiers.
    Layer 2: Static AST analysis for overlapping alternation in unbounded quantifiers.
    """
    try:
        parsed = re_parser.parse(pattern)
    except re.error:
        return

    if _has_dangerous_nesting(parsed) or _has_overlapping_alternation(parsed):
        logger.warning("Rejected unsafe regex pattern: %r", pattern)
        raise InvalidImmutabilityPolicy(_REJECTION_MESSAGE)
