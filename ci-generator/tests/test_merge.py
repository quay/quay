"""Unit tests for deep_merge."""

from generate import deep_merge


def test_nested_dicts_later_wins() -> None:
    base = {"a": {"b": 1, "c": 2}}
    overlay = {"a": {"c": 3, "d": 4}}
    assert deep_merge(base, overlay) == {"a": {"b": 1, "c": 3, "d": 4}}


def test_scalar_later_wins() -> None:
    assert deep_merge({"as": "old"}, {"as": "new"}) == {"as": "new"}


def test_list_of_maps_merges_by_index() -> None:
    base = {"tests": [{"steps": {"env": {"A": "1"}, "workflow": "ipi-aws"}}]}
    overlay = {"tests": [{"steps": {"env": {"B": "2"}, "test": [{"ref": "x"}]}}]}
    assert deep_merge(base, overlay) == {
        "tests": [
            {
                "steps": {
                    "env": {"A": "1", "B": "2"},
                    "workflow": "ipi-aws",
                    "test": [{"ref": "x"}],
                }
            }
        ]
    }


def test_list_of_maps_appends_extra_items() -> None:
    base = {"items": [{"name": "a"}]}
    overlay = {"items": [{"name": "a", "extra": True}, {"name": "b"}]}
    assert deep_merge(base, overlay) == {
        "items": [{"name": "a", "extra": True}, {"name": "b"}],
    }


def test_scalar_list_replaces() -> None:
    assert deep_merge({"post": ["a", "b"]}, {"post": ["c"]}) == {"post": ["c"]}


def test_none_overlay_keeps_base() -> None:
    assert deep_merge({"a": 1}, None) == {"a": 1}


def test_none_base_uses_overlay() -> None:
    assert deep_merge(None, {"a": 1}) == {"a": 1}
