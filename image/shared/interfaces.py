from abc import ABCMeta, abstractproperty, abstractmethod
from six import add_metaclass


@add_metaclass(ABCMeta)
class ManifestInterface(object):
    """
    Defines the interface for the various manifests types supported.
    """

    @abstractproperty
    def is_manifest_list(self):
        """
        Returns whether this manifest is a list.
        """

    @abstractproperty
    def schema_version(self):
        """
        The version of the schema.
        """

    @abstractproperty
    def digest(self):
        """
        The digest of the manifest, including type prefix.
        """
        pass

    @abstractproperty
    def media_type(self):
        """
        The media type of the schema.
        """
        pass

    @abstractproperty
    def manifest_dict(self):
        """
        Returns the manifest as a dictionary ready to be serialized to JSON.
        """
        pass

    @abstractproperty
    def bytes(self):
        """
        Returns the bytes of the manifest.
        """
        pass

    @abstractproperty
    def layers_compressed_size(self):
        """
        Returns the total compressed size of all the layers in this manifest.

        Returns None if this cannot be computed locally.
        """

    @abstractproperty
    def config_media_type(self):
        """Returns the media type of the config of this manifest or None if
        this manifest does not support a configuration type.
        """

    @abstractmethod
    def validate(self, content_retriever):
        """
        Performs validation of required assertions about the manifest.

        Raises a ManifestException on failure.
        """
        pass

    @abstractmethod
    def get_layers(self, content_retriever):
        """
        Returns the layers of this manifest, from base to leaf or None if this kind of manifest does
        not support layers.

        The layer must be of type ManifestImageLayer.
        """
        pass

    @abstractmethod
    def get_leaf_layer_v1_image_id(self, content_retriever):
        """
        Returns the Docker V1 image ID for the leaf (top) layer, if any, or None if not applicable.
        """
        pass

    @abstractmethod
    def get_legacy_image_ids(self, content_retriever):
        """
        Returns the Docker V1 image IDs for the layers of this manifest or None if not applicable.
        """
        pass

    @abstractproperty
    def blob_digests(self):
        """
        Returns an iterator over all the blob digests referenced by this manifest, from base to
        leaf.

        The blob digests are strings with prefixes. For manifests that reference config as a blob,
        the blob will be included here as the last entry.
        """

    @abstractmethod
    def get_blob_digests_for_translation(self):
        """
        Returns the blob digests for translation of this manifest into another manifest.

        This method will ignore missing IDs in layers, unlike `blob_digests`.
        """

    @abstractproperty
    def local_blob_digests(self):
        """
        Returns an iterator over all the *non-remote* blob digests referenced by this manifest, from
        base to leaf.

        The blob digests are strings with prefixes. For manifests that reference config as a blob,
        the blob will be included here as the last entry.
        """

    @abstractmethod
    def child_manifests(self, content_retriever):
        """
        Returns an iterator of all manifests that live under this manifest, if any or None if not
        applicable.
        """

    @abstractmethod
    def get_manifest_labels(self, content_retriever):
        """
        Returns a dictionary of all the labels defined inside this manifest or None if this kind of
        manifest does not support labels.
        """
        pass

    @abstractmethod
    def get_requires_empty_layer_blob(self, content_retriever):
        """
        Whether this schema requires the special empty layer blob.
        """
        pass

    @abstractmethod
    def unsigned(self):
        """
        Returns an unsigned version of this manifest.
        """

    @abstractproperty
    def has_legacy_image(self):
        """
        Returns True if this manifest has a legacy V1 image, or False if not.
        """

    @abstractmethod
    def generate_legacy_layers(self, images_map, content_retriever):
        """
        Rewrites Docker v1 image IDs and returns a generator of DockerV1Metadata, starting at the
        base layer and working towards the leaf.

        If Docker gives us a layer with a v1 image ID that already points to existing
        content, but the checksums don't match, then we need to rewrite the image ID
        to something new in order to ensure consistency.

        Returns None if there are no legacy images associated with the manifest.
        """

    @abstractmethod
    def get_schema1_manifest(self, namespace_name, repo_name, tag_name, content_retriever):
        """
        Returns a schema1 version of the manifest.

        If this is a mainfest list, should return the manifest that is compatible with V1, by virtue
        of being `amd64` and `linux`. If none, returns None.
        """

    @abstractmethod
    def convert_manifest(
        self, allowed_mediatypes, namespace_name, repo_name, tag_name, content_retriever
    ):
        """
        Returns a version of this schema that has a media type found in the given media type set.

        If not possible, or an error occurs, returns None.
        """


@add_metaclass(ABCMeta)
class ManifestListInterface(object):
    """
    Defines the interface for the various manifest list types supported.
    """

    @abstractmethod
    def amd64_linux_manifest_digest(self):
        """Returns the digest of the AMD64+Linux manifest in this list, if any, or None
        if none.
        """


@add_metaclass(ABCMeta)
class ContentRetriever(object):
    """
    Defines the interface for retrieval of various content referenced by a manifest.
    """

    @abstractmethod
    def get_manifest_bytes_with_digest(self, digest):
        """
        Returns the bytes of the manifest with the given digest or None if none found.
        """

    @abstractmethod
    def get_blob_bytes_with_digest(self, digest):
        """
        Returns the bytes of the blob with the given digest or None if none found.
        """
