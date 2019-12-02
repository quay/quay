import re

import pytest

from buildtrigger.triggerutil import matches_ref


@pytest.mark.parametrize(
    "ref, filt, matches",
    [
        ("ref/heads/master", ".+", True),
        ("ref/heads/master", "heads/.+", True),
        ("ref/heads/master", "heads/master", True),
        ("ref/heads/slash/branch", "heads/slash/branch", True),
        ("ref/heads/slash/branch", "heads/.+", True),
        ("ref/heads/foobar", "heads/master", False),
        ("ref/heads/master", "tags/master", False),
        ("ref/heads/master", "(((heads/alpha)|(heads/beta))|(heads/gamma))|(heads/master)", True),
        ("ref/heads/alpha", "(((heads/alpha)|(heads/beta))|(heads/gamma))|(heads/master)", True),
        ("ref/heads/beta", "(((heads/alpha)|(heads/beta))|(heads/gamma))|(heads/master)", True),
        ("ref/heads/gamma", "(((heads/alpha)|(heads/beta))|(heads/gamma))|(heads/master)", True),
        ("ref/heads/delta", "(((heads/alpha)|(heads/beta))|(heads/gamma))|(heads/master)", False),
    ],
)
def test_matches_ref(ref, filt, matches):
    assert matches_ref(ref, re.compile(filt)) == matches
