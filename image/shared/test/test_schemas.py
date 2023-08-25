import pytest

from image.docker.schema1 import DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE
from image.docker.schema2 import (
    DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
)
from image.docker.schema2.test.test_list import MANIFESTLIST_BYTES
from image.docker.schema2.test.test_manifest import MANIFEST_BYTES as SCHEMA2_BYTES
from image.docker.test.test_schema1 import MANIFEST_BYTES as SCHEMA1_BYTES
from image.oci import OCI_IMAGE_INDEX_CONTENT_TYPE
from image.oci.test.testdata import OCI_IMAGE_INDEX_MANIFEST
from image.shared.schemas import parse_manifest_from_bytes
from util.bytes import Bytes


@pytest.mark.parametrize(
    "media_type, manifest_bytes, sparse_manifestlist",
    [
        (DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE, SCHEMA1_BYTES, False),
        (DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE, SCHEMA2_BYTES, False),
        (DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE, MANIFESTLIST_BYTES, False),
        (DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE, MANIFESTLIST_BYTES, True),
        (OCI_IMAGE_INDEX_CONTENT_TYPE, OCI_IMAGE_INDEX_MANIFEST, False),
        (OCI_IMAGE_INDEX_CONTENT_TYPE, OCI_IMAGE_INDEX_MANIFEST, True),
    ],
)
def test_parse_manifest_from_bytes(media_type, manifest_bytes, sparse_manifestlist):
    assert parse_manifest_from_bytes(
        Bytes.for_string_or_unicode(manifest_bytes),
        media_type,
        validate=False,
        sparse_manifest_support=sparse_manifestlist,
    )
