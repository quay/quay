import json
from collections import namedtuple

from digest import digest_tools
from image.oci import OCI_IMAGE_INDEX_CONTENT_TYPE
from image.shared import ManifestException
from image.shared.interfaces import ManifestInterface, ManifestListInterface
from util.bytes import Bytes

ManifestImageLayer = namedtuple(
    "ManifestImageLayer",
    [
        "layer_id",
        "compressed_size",
        "is_remote",
        "urls",
        "command",
        "blob_digest",
        "created_datetime",
        "author",
        "comment",
        "internal_layer",
    ],
)


class ManifestReference(ManifestInterface):
    """
    References a manifest's descriptor properties in a manifest list.

    See https://github.com/opencontainers/image-spec/blob/main/descriptor.md#properties
    for details.

    Sample payload:
    {
      "digest": "sha256:b69959407d21e8a062e0416bf13405bb2b71ed7a84dde4158ebafacfa06f5578",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "amd64",
        "os": "linux"
      },
      "size": 527
    }
    """

    def __init__(self, manifest_bytes: Bytes, validate=False):
        assert isinstance(manifest_bytes, Bytes)
        self._payload = manifest_bytes
        try:
            self._parsed = json.loads(self._payload.as_unicode())
        except ValueError as e:
            raise ManifestException(f"malformed manifest data: {e}")

    @property
    def is_manifest_list(self):
        """
        Returns whether this manifest is a list.
        """
        return False

    @property
    def schema_version(self):
        """
        The version of the schema.
        """
        # return self._parsed["schemaVersion"]
        # does not exist in manifest reference
        pass

    @property
    def digest(self):
        """
        The digest of the manifest, including type prefix.
        """
        return self._parsed["digest"]

    @property
    def media_type(self):
        """
        The media type of the schema.
        """
        return self._parsed["mediaType"]

    @property
    def artifact_type(self):
        """
        The artifact type of the manifest.
        """
        return self._parsed.get("artifactType")

    @property
    def subject(self):
        """
        The subject of the manifest.
        """
        return self._parsed.get("subject")

    @property
    def manifest_dict(self):
        """
        Returns the manifest as a dictionary ready to be serialized to JSON.
        """
        return self._parsed

    @property
    def bytes(self):
        """
        Returns the bytes of the manifest.
        """
        return Bytes.for_string_or_unicode("")

    @property
    def layers_compressed_size(self):
        """
        Returns the total compressed size of all the layers in this manifest.

        Returns None if this cannot be computed locally.
        """
        # don't have this information at this point
        return None

    @property
    def config(self):
        """
        Returns the config of this manifest or None if this manifest does not
        support a configuration type.
        """
        pass

    @property
    def config_media_type(self):
        """Returns the media type of the config of this manifest or None if
        this manifest does not support a configuration type.
        """
        pass

    def validate(self, content_retriever):
        """
        Performs validation of required assertions about the manifest.

        Raises a ManifestException on failure.
        """
        pass

    @property
    def filesystem_layers(self):
        """
        Returns the file system layers of this manifest, from base to leaf.
        """
        pass

    def get_layers(self, content_retriever):
        """
        Returns the layers of this manifest, from base to leaf or None if this kind of manifest does
        not support layers.

        The layer must be of type ManifestImageLayer.
        """
        pass

    def get_leaf_layer_v1_image_id(self, content_retriever):
        """
        Returns the Docker V1 image ID for the leaf (top) layer, if any, or None if not applicable.
        """
        pass

    def get_legacy_image_ids(self, content_retriever):
        """
        Returns the Docker V1 image IDs for the layers of this manifest or None if not applicable.
        """
        pass

    @property
    def blob_digests(self):
        """
        Returns an iterator over all the blob digests referenced by this manifest, from base to
        leaf.

        The blob digests are strings with prefixes. For manifests that reference config as a blob,
        the blob will be included here as the last entry.
        """
        pass

    def get_blob_digests_for_translation(self):
        """
        Returns the blob digests for translation of this manifest into another manifest.

        This method will ignore missing IDs in layers, unlike `blob_digests`.
        """
        pass

    @property
    def local_blob_digests(self):
        """
        Returns an iterator over all the *non-remote* blob digests referenced by this manifest, from
        base to leaf.

        The blob digests are strings with prefixes. For manifests that reference config as a blob,
        the blob will be included here as the last entry.
        """
        pass

    def child_manifests(self, content_retriever):
        """
        Returns an iterator of all manifests that live under this manifest, if any or None if not
        applicable.
        """
        return None

    def get_manifest_labels(self, content_retriever):
        """
        Returns a dictionary of all the labels defined inside this manifest or None if this kind of
        manifest does not support labels.
        """
        return None

    def get_requires_empty_layer_blob(self, content_retriever):
        """
        Whether this schema requires the special empty layer blob.
        """
        return None

    def unsigned(self):
        """
        Returns an unsigned version of this manifest.
        """
        pass

    @property
    def has_legacy_image(self):
        """
        Returns True if this manifest has a legacy V1 image, or False if not.
        """
        pass

    def generate_legacy_layers(self, images_map, content_retriever):
        """
        Rewrites Docker v1 image IDs and returns a generator of DockerV1Metadata, starting at the
        base layer and working towards the leaf.

        If Docker gives us a layer with a v1 image ID that already points to existing
        content, but the checksums don't match, then we need to rewrite the image ID
        to something new in order to ensure consistency.

        Returns None if there are no legacy images associated with the manifest.
        """
        pass

    def get_schema1_manifest(self, namespace_name, repo_name, tag_name, content_retriever):
        """
        Returns a schema1 version of the manifest.

        If this is a mainfest list, should return the manifest that is compatible with V1, by virtue
        of being `amd64` and `linux`. If none, returns None.
        """
        pass

    def convert_manifest(
        self, allowed_mediatypes, namespace_name, repo_name, tag_name, content_retriever
    ):
        """
        Returns a version of this schema that has a media type found in the given media type set.

        If not possible, or an error occurs, returns None.
        """
        pass


class SparseManifestList(ManifestListInterface):
    """
    Represents a manifest list or OCI index where not all sub-manifests are
    expected to exist in Quay.
    """

    def __init__(self, manifest_bytes: Bytes, media_type, validate=False):
        assert isinstance(manifest_bytes, Bytes)
        self._payload = manifest_bytes
        self._media_type = media_type
        try:
            self._parsed = json.loads(self._payload.as_unicode())
        except ValueError as e:
            raise ManifestException(f"malformed manifest data: {e}")

    @property
    def schema_version(self):
        """
        The version of the schema.
        """
        return self._parsed["schemaVersion"]

    @property
    def digest(self):
        """
        The digest of the manifest, including type prefix.
        """
        return digest_tools.sha256_digest(self._payload.as_encoded_str())

    @property
    def media_type(self):
        """
        The media type of the schema.
        """
        return self._media_type

    @property
    def artifact_type(self):
        """
        The artifact type of the manifest.
        """
        return self._parsed.get("artifactType")

    @property
    def subject(self):
        """
        The subject of the manifest.
        """
        return self._parsed.get("subject")

    @property
    def is_manifest_list(self):
        return True

    def child_manifests(self, content_retriever):
        """
        Returns an iterator of all manifests that live under this manifest, if
        any or None if not applicable.

        Ignored content_retriever argument, getting the child manifests from the
        raw manifest instead.
        """
        for manifest in self._parsed["manifests"]:
            mbytes = json.dumps(manifest)
            yield ManifestReference(Bytes.for_string_or_unicode(mbytes))

    @property
    def amd64_linux_manifest_digest(self):
        """
        Returns the digest of the AMD64+Linux manifest in this list, if any, or
        None if none.
        """
        digest = None
        for manifest in self._parsed["manifests"]:
            platform = manifest["platform"]
            if platform["architecture"] == "amd64" and platform["os"] == "linux":
                digest = manifest["digest"]
                break
        return digest

    @property
    def manifest_dict(self):
        """
        Returns the manifest as a dictionary ready to be serialized to JSON.
        """
        return self._parsed

    @property
    def bytes(self):
        """
        Returns the bytes of the manifest.
        """
        return self._payload

    @property
    def layers_compressed_size(self):
        """
        Returns the total compressed size of all the layers in this manifest.

        Returns None if this cannot be computed locally.
        """
        # don't have this information at this point
        return None

    @property
    def config(self):
        """
        Returns the config of this manifest or None if this manifest does not
        support a configuration type.
        """
        return None

    @property
    def config_media_type(self):
        """Returns the media type of the config of this manifest or None if
        this manifest does not support a configuration type.
        """
        pass

    def validate(self, content_retriever):
        """
        Performs validation of required assertions about the manifest.

        Raises a ManifestException on failure.
        """
        pass

    @property
    def filesystem_layers(self):
        """
        Returns the file system layers of this manifest, from base to leaf.
        """
        return None

    def get_layers(self, content_retriever):
        """
        Returns the layers of this manifest, from base to leaf or None if this kind of manifest does
        not support layers.

        The layer must be of type ManifestImageLayer.
        """
        pass

    def get_leaf_layer_v1_image_id(self, content_retriever):
        """
        Returns the Docker V1 image ID for the leaf (top) layer, if any, or None if not applicable.
        """
        pass

    def get_legacy_image_ids(self, content_retriever):
        """
        Returns the Docker V1 image IDs for the layers of this manifest or None if not applicable.
        """
        pass

    @property
    def blob_digests(self):
        """
        Returns an iterator over all the blob digests referenced by this manifest, from base to
        leaf.

        The blob digests are strings with prefixes. For manifests that reference config as a blob,
        the blob will be included here as the last entry.
        """
        pass

    def get_blob_digests_for_translation(self):
        """
        Returns the blob digests for translation of this manifest into another manifest.

        This method will ignore missing IDs in layers, unlike `blob_digests`.
        """
        pass

    @property
    def local_blob_digests(self):
        """
        Returns an iterator over all the *non-remote* blob digests referenced by this manifest, from
        base to leaf.

        The blob digests are strings with prefixes. For manifests that reference config as a blob,
        the blob will be included here as the last entry.
        """
        pass

    def get_manifest_labels(self, content_retriever):
        """
        Returns a dictionary of all the labels defined inside this manifest or None if this kind of
        manifest does not support labels.
        """
        return None

    def get_requires_empty_layer_blob(self, content_retriever):
        """
        Whether this schema requires the special empty layer blob.
        """
        return None

    def unsigned(self):
        """
        Returns an unsigned version of this manifest.
        """
        pass

    @property
    def has_legacy_image(self):
        """
        Returns True if this manifest has a legacy V1 image, or False if not.
        """
        pass

    def generate_legacy_layers(self, images_map, content_retriever):
        """
        Rewrites Docker v1 image IDs and returns a generator of DockerV1Metadata, starting at the
        base layer and working towards the leaf.

        If Docker gives us a layer with a v1 image ID that already points to existing
        content, but the checksums don't match, then we need to rewrite the image ID
        to something new in order to ensure consistency.

        Returns None if there are no legacy images associated with the manifest.
        """
        pass

    def get_schema1_manifest(self, namespace_name, repo_name, tag_name, content_retriever):
        """
        Returns a schema1 version of the manifest.

        If this is a mainfest list, should return the manifest that is compatible with V1, by virtue
        of being `amd64` and `linux`. If none, returns None.
        """
        pass

    def convert_manifest(
        self, allowed_mediatypes, namespace_name, repo_name, tag_name, content_retriever
    ):
        """
        Returns a version of this schema that has a media type found in the given media type set.

        If not possible, or an error occurs, returns None.
        """
        pass
