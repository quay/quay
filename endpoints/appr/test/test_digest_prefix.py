import pytest
from endpoints.appr.models_cnr import _strip_sha256_header


@pytest.mark.parametrize(
    "digest,expected",
    [
        (
            "sha256:251b6897608fb18b8a91ac9abac686e2e95245d5a041f2d1e78fe7a815e6480a",
            "251b6897608fb18b8a91ac9abac686e2e95245d5a041f2d1e78fe7a815e6480a",
        ),
        (
            "251b6897608fb18b8a91ac9abac686e2e95245d5a041f2d1e78fe7a815e6480a",
            "251b6897608fb18b8a91ac9abac686e2e95245d5a041f2d1e78fe7a815e6480a",
        ),
    ],
)
def test_stip_sha256(digest, expected):
    assert _strip_sha256_header(digest) == expected
