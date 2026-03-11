from unittest.mock import MagicMock, patch

import pytest

from util.repomirror.skopeomirror import SkopeoMirror


class TestSkopeoCopyPreserveSignatures:
    """Tests that SkopeoMirror.copy() builds correct CLI args for preserve_signatures."""

    @pytest.fixture
    def skopeo(self):
        return SkopeoMirror()

    @pytest.fixture
    def copy_defaults(self):
        return {
            "src_image": "docker://registry.example.com/repo:v1",
            "dest_image": "docker://quay.example.com/repo:v1",
            "timeout": 300,
            "proxy": {},
        }

    @pytest.fixture
    def mock_popen(self):
        with patch("util.repomirror.skopeomirror.subprocess.Popen") as mock:
            proc = MagicMock()
            proc.returncode = 0
            mock.return_value = proc
            yield mock

    def test_remove_signatures_present_by_default(self, mock_popen, skopeo, copy_defaults):
        """Default behavior: --remove-signatures is in the args."""
        skopeo.copy(**copy_defaults)

        args = mock_popen.call_args[0][0]
        assert "--remove-signatures" in args

    def test_remove_signatures_present_when_preserve_false(self, mock_popen, skopeo, copy_defaults):
        """Explicit preserve_signatures=False: --remove-signatures is in the args."""
        skopeo.copy(**copy_defaults, preserve_signatures=False)

        args = mock_popen.call_args[0][0]
        assert "--remove-signatures" in args

    def test_remove_signatures_absent_when_preserve_true(self, mock_popen, skopeo, copy_defaults):
        """preserve_signatures=True: --remove-signatures must NOT be in the args."""
        skopeo.copy(**copy_defaults, preserve_signatures=True)

        args = mock_popen.call_args[0][0]
        assert "--remove-signatures" not in args

    def test_copy_all_flag_always_present(self, mock_popen, skopeo, copy_defaults):
        """--all flag should be present regardless of preserve_signatures."""
        skopeo.copy(**copy_defaults, preserve_signatures=True)
        args_preserve = mock_popen.call_args[0][0]

        skopeo.copy(**copy_defaults, preserve_signatures=False)
        args_strip = mock_popen.call_args[0][0]

        assert "--all" in args_preserve
        assert "--all" in args_strip
