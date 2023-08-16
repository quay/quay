import json

import pytest

from image.oci.index import MalformedIndex, OCIIndex
from image.oci.test.testdata import (
    OCI_IMAGE_INDEX_MANIFEST,
    OCI_IMAGE_INDEX_MANIFEST_WITHOUT_AMD,
)
from util.bytes import Bytes


def test_parse_basic_index():
    index = OCIIndex(Bytes.for_string_or_unicode(OCI_IMAGE_INDEX_MANIFEST))
    assert index.is_manifest_list
    assert index.digest == "sha256:6416299892584b515393076863b75f192ca6cf98583d83b8e583ec3b6f2a8a5e"
    assert index.local_blob_digests == []
    assert index.child_manifest_digests() == [
        "sha256:31dd947a0acb5d8b840dc0de40a74f336e08cb0e17ba951c2faaea6374c1a0f3",
        "sha256:4eca3b97fcd88a47c6454d0cb9ff59aeb4baeca332387e87421b2302bfc724e6",
        "sha256:dacec655f2712b6f5eabc007b154959bba7add6aafdcab883e314f16e491f9d3",
    ]
    assert (
        index.amd64_linux_manifest_digest
        == "sha256:31dd947a0acb5d8b840dc0de40a74f336e08cb0e17ba951c2faaea6374c1a0f3"
    )


def test_config_missing_required():
    valid_index = json.loads(OCI_IMAGE_INDEX_MANIFEST)
    valid_index.pop("schemaVersion")

    with pytest.raises(MalformedIndex):
        OCIIndex(Bytes.for_string_or_unicode(json.dumps(valid_index)))


def test_invalid_index():
    with pytest.raises(MalformedIndex):
        OCIIndex(Bytes.for_string_or_unicode("{}"))


def test_index_without_amd():
    index = OCIIndex(Bytes.for_string_or_unicode(OCI_IMAGE_INDEX_MANIFEST_WITHOUT_AMD))
    assert index.is_manifest_list
    assert index.digest == "sha256:a0ed0f2b3949bc731063320667062307faf4245f6872dc5bc98ee6ea5443f169"
    assert index.local_blob_digests == []
    assert index.child_manifest_digests() == [
        "sha256:e692418e4cbaf90ca69d05a66403747baa33ee08806650b51fab815ad7fc331f",
        "sha256:5b0bcabd1ed22e9fb1310cf6c2dec7cdef19f0ad69efa1f392e94a4333501270",
    ]
    assert index.amd64_linux_manifest_digest is None
