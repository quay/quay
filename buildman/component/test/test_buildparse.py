import pytest

from buildman.component.buildparse import extract_current_step


@pytest.mark.parametrize(
    "input,expected_step",
    [
        ("", None),
        ("Step a :", None),
        ("Step 1 :", 1),
        ("Step 1 : ", 1),
        ("Step 1/2 : ", 1),
        ("Step 2/17 : ", 2),
        ("Step 4/13 : ARG somearg=foo", 4),
    ],
)
def test_extract_current_step(input, expected_step):
    assert extract_current_step(input) == expected_step
