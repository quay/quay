import pytest

from util import slash_join


@pytest.mark.parametrize(
    "pieces, expected",
    [
        (
            ["https://github.com", "/coreos-inc/" "quay/pull/1092/files"],
            "https://github.com/coreos-inc/quay/pull/1092/files",
        ),
        (
            ["https://", "github.com/", "/coreos-inc", "/quay/pull/1092/files/"],
            "https://github.com/coreos-inc/quay/pull/1092/files",
        ),
        (["https://somegithub.com/", "/api/v3/"], "https://somegithub.com/api/v3"),
        (["https://github.somedomain.com/", "/api/v3/"], "https://github.somedomain.com/api/v3"),
    ],
)
def test_slash_join(pieces, expected):
    joined_url = slash_join(*pieces)
    assert joined_url == expected
