from image.docker.schema1 import DOCKER_SCHEMA1_CONTENT_TYPES, DockerSchema1Manifest
from image.docker.schema2 import (
    DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
)
from image.docker.schema2.list import DockerSchema2ManifestList
from image.docker.schema2.manifest import DockerSchema2Manifest
from image.oci import OCI_IMAGE_INDEX_CONTENT_TYPE, OCI_IMAGE_MANIFEST_CONTENT_TYPE
from image.oci.index import OCIIndex
from image.oci.manifest import OCIManifest
from image.shared import ManifestException
from image.shared.types import SparseManifestList
from util.bytes import Bytes

MANIFEST_LIST_TYPES = [DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE, OCI_IMAGE_INDEX_CONTENT_TYPE]


def is_manifest_list_type(content_type):
    """Returns True if the given content type refers to a manifest list of some kind."""
    return content_type in MANIFEST_LIST_TYPES


def parse_manifest_from_bytes(
    manifest_bytes,
    media_type,
    validate=True,
    sparse_manifest_support=False,
):
    """
    Parses and returns a manifest from the given bytes, for the given media type.

    Raises a ManifestException if the parse fails for some reason.
    """
    assert isinstance(manifest_bytes, Bytes)

    if is_manifest_list_type(media_type) and sparse_manifest_support:
        return SparseManifestList(manifest_bytes, media_type)

    if media_type == DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE:
        return DockerSchema2Manifest(manifest_bytes)

    if media_type == DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE:
        return DockerSchema2ManifestList(manifest_bytes)

    if media_type == OCI_IMAGE_MANIFEST_CONTENT_TYPE:
        return OCIManifest(manifest_bytes)

    if media_type == OCI_IMAGE_INDEX_CONTENT_TYPE:
        return OCIIndex(manifest_bytes)

    if media_type in DOCKER_SCHEMA1_CONTENT_TYPES:
        return DockerSchema1Manifest(manifest_bytes, validate=validate)

    raise ManifestException("Unknown or unsupported manifest media type `%s`" % media_type)
