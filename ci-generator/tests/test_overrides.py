"""Override matching and specificity ordering."""

from pathlib import Path

from generate import apply_overrides, load_overrides, override_matches
from model import Cell, Override


def _cell(**kwargs: str) -> Cell:
    values = {
        "org": "quay",
        "repo": "quay",
        "branch": "redhat-3.18",
        "quay_version": "3.18",
        "ocp_version": "4.22",
        "cloud": "aws",
        "test": "e2e-install",
        "tier": "weekly",
    }
    values.update(kwargs)
    return Cell(**values)


def test_override_matches_all_keys() -> None:
    cell = _cell()
    assert override_matches({"quay": "3.18", "ocp": "4.22", "cloud": "aws"}, cell)
    assert not override_matches({"quay": "3.18", "ocp": "4.21"}, cell)


def test_empty_match_is_global() -> None:
    assert override_matches({}, _cell())


def test_specificity_sorts_broad_first(tmp_path: Path) -> None:
    (tmp_path / "specific.yaml").write_text("match:\n  quay: '3.18'\n  ocp: '4.22'\nvalue: specific\n")
    (tmp_path / "broad.yaml").write_text("match:\n  quay: '3.18'\nvalue: broad\n")
    loaded = load_overrides(tmp_path)
    assert [item.path.name for item in loaded] == ["broad.yaml", "specific.yaml"]
    assert loaded[0].specificity < loaded[1].specificity


def test_later_specific_override_wins() -> None:
    cell = _cell()
    overrides = [
        Override(path=Path("broad.yaml"), match={"quay": "3.18"}, patch={"cron": "broad"}),
        Override(
            path=Path("specific.yaml"),
            match={"quay": "3.18", "ocp": "4.22"},
            patch={"cron": "specific"},
        ),
    ]
    merged = apply_overrides({"cron": "default"}, cell, overrides)
    assert merged["cron"] == "specific"
