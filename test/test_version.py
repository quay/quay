import os
from unittest.mock import patch

import pytest

import _init


@pytest.fixture()
def quay_root(tmp_path):
    """Create a temporary directory simulating the Quay root with a CHANGELOG.md."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n"
        "## [v3.18.0] - 2026-07-01\n\n"
        "### Added\n- New features\n\n"
        "## [v3.17.0] - 2026-01-01\n"
    )
    return tmp_path


class TestGetVersionNumber:
    def test_explicit_env_takes_precedence(self, quay_root):
        (quay_root / "BUILD_DATE").write_text("20260803\n")
        with (
            patch.object(_init, "ROOT_DIR", str(quay_root)),
            patch.dict(os.environ, {"QUAY_VERSION": "v3.18.0"}),
        ):
            assert _init._get_version_number() == "v3.18.0"

    def test_nightly_format_when_build_date_exists(self, quay_root):
        (quay_root / "BUILD_DATE").write_text("20260803\n")
        with (
            patch.object(_init, "ROOT_DIR", str(quay_root)),
            patch.dict(os.environ, {}, clear=False),
        ):
            os.environ.pop("QUAY_VERSION", None)
            assert _init._get_version_number() == "v3.18.0-nightly-20260803"

    def test_changelog_fallback_when_no_build_date(self, quay_root):
        with (
            patch.object(_init, "ROOT_DIR", str(quay_root)),
            patch.dict(os.environ, {}, clear=False),
        ):
            os.environ.pop("QUAY_VERSION", None)
            assert _init._get_version_number() == "v3.18.0"

    def test_empty_when_no_changelog_and_no_env(self, tmp_path):
        with (
            patch.object(_init, "ROOT_DIR", str(tmp_path)),
            patch.dict(os.environ, {}, clear=False),
        ):
            os.environ.pop("QUAY_VERSION", None)
            assert _init._get_version_number() == ""

    def test_local_dev_env_passthrough(self, quay_root):
        with (
            patch.object(_init, "ROOT_DIR", str(quay_root)),
            patch.dict(os.environ, {"QUAY_VERSION": "local-dev"}),
        ):
            assert _init._get_version_number() == "local-dev"

    def test_changelog_without_version_entry_returns_empty(self, tmp_path):
        (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\nNo releases yet.\n")
        with (
            patch.object(_init, "ROOT_DIR", str(tmp_path)),
            patch.dict(os.environ, {}, clear=False),
        ):
            os.environ.pop("QUAY_VERSION", None)
            assert _init._get_version_number() == ""


class TestGetBuildDate:
    def test_reads_build_date_file(self, tmp_path):
        (tmp_path / "BUILD_DATE").write_text("20260804\n")
        with patch.object(_init, "ROOT_DIR", str(tmp_path)):
            assert _init._get_build_date() == "20260804"

    def test_returns_empty_when_file_missing(self, tmp_path):
        with patch.object(_init, "ROOT_DIR", str(tmp_path)):
            assert _init._get_build_date() == ""
