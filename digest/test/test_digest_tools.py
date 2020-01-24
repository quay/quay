import pytest

from digest.digest_tools import Digest, content_path, InvalidDigestException


@pytest.mark.parametrize(
    "digest, output_args",
    [
        ("tarsum.v123123+sha1:123deadbeef", ("tarsum.v123123+sha1", "123deadbeef")),
        ("tarsum.v1+sha256:123123", ("tarsum.v1+sha256", "123123")),
        ("tarsum.v0+md5:abc", ("tarsum.v0+md5", "abc")),
        ("tarsum+sha1:abc", ("tarsum+sha1", "abc")),
        ("sha1:123deadbeef", ("sha1", "123deadbeef")),
        ("sha256:123123", ("sha256", "123123")),
        ("md5:abc", ("md5", "abc")),
    ],
)
def test_parse_good(digest, output_args):
    assert Digest.parse_digest(digest) == Digest(*output_args)
    assert str(Digest.parse_digest(digest)) == digest


@pytest.mark.parametrize(
    "bad_digest",
    [
        "tarsum.v+md5:abc:",
        "sha1:123deadbeefzxczxv",
        "sha256123123",
        "tarsum.v1+",
        "tarsum.v1123+sha1:",
        "sha256:👌",
    ],
)
def test_parse_fail(bad_digest):
    with pytest.raises(InvalidDigestException):
        Digest.parse_digest(bad_digest)


@pytest.mark.parametrize(
    "digest, path",
    [
        ("tarsum.v123123+sha1:123deadbeef", "tarsum/v123123/sha1/12/123deadbeef"),
        ("tarsum.v1+sha256:123123", "tarsum/v1/sha256/12/123123"),
        ("tarsum.v0+md5:abc", "tarsum/v0/md5/ab/abc"),
        ("sha1:123deadbeef", "sha1/12/123deadbeef"),
        ("sha256:123123", "sha256/12/123123"),
        ("md5:abc", "md5/ab/abc"),
        ("md5:1", "md5/01/1"),
        ("md5.....+++:1", "md5/01/1"),
        (".md5.:1", "md5/01/1"),
    ],
)
def test_paths(digest, path):
    assert content_path(digest) == path
