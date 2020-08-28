"""
Implements validation and conversion for the OCI Manifest JSON.

See: https://github.com/opencontainers/image-spec/blob/master/manifest.md

Example:

{
  "schemaVersion": 2,
  "config": {
    "mediaType": "application/vnd.oci.image.config.v1+json",
    "size": 7023,
    "digest": "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7"
  },
  "layers": [
    {
      "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
      "size": 32654,
      "digest": "sha256:9834876dcfb05cb167a5c24953eba58c4ac89b1adf57f28f2f9d09af107ee8f0"
    },
    {
      "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
      "size": 16724,
      "digest": "sha256:3c3a4604a545cdc127456d94e421cd355bca5b528f4a9c1905b15da2eb4a4c6b"
    },
    {
      "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
      "size": 73109,
      "digest": "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736"
    }
  ],
  "annotations": {
    "com.example.key1": "value1",
    "com.example.key2": "value2"
  }
}

"""

import json
import logging
import hashlib

from collections import namedtuple
from jsonschema import validate as validate_schema, ValidationError

from digest import digest_tools
from image.shared import ManifestException
from image.shared.interfaces import ManifestInterface
from image.shared.types import ManifestImageLayer
from image.docker.schema2 import EMPTY_LAYER_BLOB_DIGEST, EMPTY_LAYER_SIZE
from image.oci import (
    OCI_IMAGE_MANIFEST_CONTENT_TYPE,
    OCI_IMAGE_CONFIG_CONTENT_TYPE,
    OCI_IMAGE_LAYER_CONTENT_TYPES,
    OCI_IMAGE_NON_DISTRIBUTABLE_LAYER_CONTENT_TYPES,
    OCI_IMAGE_TAR_GZIP_LAYER_CONTENT_TYPE,
    OCI_IMAGE_TAR_GZIP_NON_DISTRIBUTABLE_LAYER_CONTENT_TYPE,
    ADDITIONAL_LAYER_CONTENT_TYPES,
    ALLOWED_ARTIFACT_TYPES,
)
from image.oci.config import OCIConfig
from image.oci.descriptor import get_descriptor_schema
from image.docker.schema1 import DockerSchema1ManifestBuilder
from util.bytes import Bytes

# Keys.
OCI_MANIFEST_VERSION_KEY = "schemaVersion"
OCI_MANIFEST_MEDIATYPE_KEY = "mediaType"
OCI_MANIFEST_CONFIG_KEY = "config"
OCI_MANIFEST_SIZE_KEY = "size"
OCI_MANIFEST_DIGEST_KEY = "digest"
OCI_MANIFEST_LAYERS_KEY = "layers"
OCI_MANIFEST_URLS_KEY = "urls"
OCI_MANIFEST_ANNOTATIONS_KEY = "annotations"

# Named tuples.
OCIManifestConfig = namedtuple("OCIManifestConfig", ["size", "digest"])
OCIManifestLayer = namedtuple(
    "OCIManifestLayer", ["index", "digest", "is_remote", "urls", "compressed_size"]
)

OCIManifestImageLayer = namedtuple(
    "OCIManifestImageLayer",
    ["history", "blob_layer", "v1_id", "v1_parent_id", "compressed_size", "blob_digest"],
)

logger = logging.getLogger(__name__)


class MalformedOCIManifest(ManifestException):
    """
    Raised when a manifest fails an assertion that should be true according to the OCI Manifest
    spec.
    """

    pass


class OCIManifest(ManifestInterface):
    def get_meta_schema(self):
        """
        Since the layers are dynamic based on config, populate them here before using
        """
        METASCHEMA = {
            "type": "object",
            "properties": {
                OCI_MANIFEST_VERSION_KEY: {
                    "type": "number",
                    "description": "The version of the schema. Must always be `2`.",
                    "minimum": 2,
                    "maximum": 2,
                },
                OCI_MANIFEST_MEDIATYPE_KEY: {
                    "type": "string",
                    "description": "The media type of the schema.",
                    "enum": [OCI_IMAGE_MANIFEST_CONTENT_TYPE],
                },
                OCI_MANIFEST_CONFIG_KEY: get_descriptor_schema(ALLOWED_ARTIFACT_TYPES),
                OCI_MANIFEST_LAYERS_KEY: {
                    "type": "array",
                    "description": "The array MUST have the base layer at index 0. Subsequent layers MUST then follow in stack order (i.e. from layers[0] to layers[len(layers)-1])",
                    "items": get_descriptor_schema(
                        OCI_IMAGE_LAYER_CONTENT_TYPES + ADDITIONAL_LAYER_CONTENT_TYPES
                    ),
                },
            },
            "required": [
                OCI_MANIFEST_VERSION_KEY,
                OCI_MANIFEST_CONFIG_KEY,
                OCI_MANIFEST_LAYERS_KEY,
            ],
        }

        return METASCHEMA

    def __init__(self, manifest_bytes, validate=False):
        assert isinstance(manifest_bytes, Bytes)

        self._payload = manifest_bytes

        self._filesystem_layers = None
        self._cached_built_config = None

        try:
            self._parsed = json.loads(self._payload.as_unicode())
        except ValueError as ve:
            raise MalformedOCIManifest("malformed manifest data: %s" % ve)

        try:
            validate_schema(self._parsed, self.get_meta_schema())
        except ValidationError as ve:
            raise MalformedOCIManifest("manifest data does not match schema: %s" % ve)

        for layer in self.filesystem_layers:
            if layer.is_remote and not layer.urls:
                raise MalformedOCIManifest("missing `urls` for remote layer")

    def validate(self, content_retriever):
        """
        Performs validation of required assertions about the manifest.

        Raises a ManifestException on failure.
        """
        # Nothing to validate.

    @property
    def is_manifest_list(self):
        return False

    @property
    def schema_version(self):
        return 2

    @property
    def manifest_dict(self):
        return self._parsed

    @property
    def media_type(self):
        return OCI_IMAGE_MANIFEST_CONTENT_TYPE

    @property
    def digest(self):
        return digest_tools.sha256_digest(self._payload.as_encoded_str())

    @property
    def config(self):
        config = self._parsed[OCI_MANIFEST_CONFIG_KEY]
        return OCIManifestConfig(
            size=config[OCI_MANIFEST_SIZE_KEY], digest=config[OCI_MANIFEST_DIGEST_KEY],
        )

    @property
    def filesystem_layers(self):
        """
        Returns the file system layers of this manifest, from base to leaf.
        """
        if self._filesystem_layers is None:
            self._filesystem_layers = list(self._generate_filesystem_layers())
        return self._filesystem_layers

    @property
    def leaf_filesystem_layer(self):
        """
        Returns the leaf file system layer for this manifest.
        """
        return self.filesystem_layers[-1]

    @property
    def config_media_type(self):
        return self._parsed[OCI_MANIFEST_CONFIG_KEY][OCI_MANIFEST_MEDIATYPE_KEY]

    @property
    def layers_compressed_size(self):
        return sum(layer.compressed_size for layer in self.filesystem_layers)

    @property
    def has_remote_layer(self):
        for layer in self.filesystem_layers:
            if layer.is_remote:
                return True

        return False

    @property
    def is_image_manifest(self):
        return self.manifest_dict["config"]["mediaType"] == OCI_IMAGE_CONFIG_CONTENT_TYPE

    @property
    def blob_digests(self):
        return [str(layer.digest) for layer in self.filesystem_layers] + [str(self.config.digest)]

    @property
    def local_blob_digests(self):
        return [str(layer.digest) for layer in self.filesystem_layers if not layer.is_remote] + [
            str(self.config.digest)
        ]

    @property
    def annotations(self):
        """ Returns the annotations on the manifest itself. """
        return self._parsed.get(OCI_MANIFEST_ANNOTATIONS_KEY) or {}

    def get_blob_digests_for_translation(self):
        return self.blob_digests

    def get_manifest_labels(self, content_retriever):
        if not self.is_image_manifest:
            return dict(self.annotations)

        built_config = self._get_built_config(content_retriever)

        labels = {}
        labels.update(built_config.labels or {})
        labels.update(self.annotations)
        return labels

    def get_layers(self, content_retriever):
        """
        Returns the layers of this manifest, from base to leaf or None if this kind of manifest does
        not support layers.
        """
        if not self.is_image_manifest:
            return

        for image_layer in self._manifest_image_layers(content_retriever):
            is_remote = image_layer.blob_layer.is_remote if image_layer.blob_layer else False
            urls = image_layer.blob_layer.urls if image_layer.blob_layer else None
            yield ManifestImageLayer(
                layer_id=image_layer.v1_id,
                compressed_size=image_layer.compressed_size,
                is_remote=is_remote,
                urls=urls,
                command=image_layer.history.command,
                blob_digest=image_layer.blob_digest,
                created_datetime=image_layer.history.created_datetime,
                author=image_layer.history.author,
                comment=image_layer.history.comment,
                internal_layer=image_layer,
            )

    @property
    def bytes(self):
        return self._payload

    def child_manifests(self, content_retriever):
        return None

    def _manifest_image_layers(self, content_retriever):
        assert self.is_image_manifest

        # Retrieve the configuration for the manifest.
        config = self._get_built_config(content_retriever)
        history = list(config.history)

        digest_history = hashlib.sha256()
        v1_layer_parent_id = None
        v1_layer_id = None

        # The history entry in OCI config is optional. If none was given, then generate the
        # "images" based on the layer data, with empty config (with exception of the final layer).
        if not history:
            for index, filesystem_layer in enumerate(self.filesystem_layers):
                digest_history.update(str(filesystem_layer.digest).encode("ascii"))
                digest_history.update(b"||")

                v1_layer_parent_id = v1_layer_id
                v1_layer_id = digest_history.hexdigest()

                yield OCIManifestImageLayer(
                    history=config.synthesized_history
                    if index == len(self.filesystem_layers) - 1
                    else None,
                    blob_layer=filesystem_layer,
                    blob_digest=str(filesystem_layer.digest),
                    v1_id=v1_layer_id,
                    v1_parent_id=v1_layer_parent_id,
                    compressed_size=filesystem_layer.compressed_size,
                )
            return

        # Make sure we aren't missing any history entries if it was specified.
        if len(history) < len(self.filesystem_layers):
            raise MalformedOCIManifest(
                "Found less history (%s) than layer blobs (%s)"
                % (len(history), len(self.filesystem_layers))
            )

        blob_index = 0
        for history_index, history_entry in enumerate(history):
            if not history_entry.is_empty and blob_index >= len(self.filesystem_layers):
                raise MalformedOCIManifest("Missing history entry #%s" % blob_index)

            v1_layer_parent_id = v1_layer_id
            blob_layer = None if history_entry.is_empty else self.filesystem_layers[blob_index]
            blob_digest = EMPTY_LAYER_BLOB_DIGEST if blob_layer is None else str(blob_layer.digest)
            compressed_size = EMPTY_LAYER_SIZE if blob_layer is None else blob_layer.compressed_size

            # Create a new synthesized V1 ID for the history layer by hashing its content and
            # the blob associated with it.
            digest_history.update(json.dumps(history_entry.raw_entry).encode("utf-8"))
            digest_history.update(b"|")
            digest_history.update(b"%d" % history_index)
            digest_history.update(b"|")
            digest_history.update(blob_digest.encode("ascii"))
            digest_history.update(b"||")

            v1_layer_id = digest_history.hexdigest()
            yield OCIManifestImageLayer(
                history=history_entry,
                blob_layer=blob_layer,
                blob_digest=blob_digest,
                v1_id=v1_layer_id,
                v1_parent_id=v1_layer_parent_id,
                compressed_size=compressed_size,
            )

            if not history_entry.is_empty:
                blob_index += 1

    @property
    def is_empty_manifest(self):
        return len(self._parsed[OCI_MANIFEST_LAYERS_KEY]) == 0

    @property
    def has_legacy_image(self):
        return self.is_image_manifest and not self.has_remote_layer and not self.is_empty_manifest

    def generate_legacy_layers(self, images_map, content_retriever):
        assert not self.has_remote_layer
        assert self.is_image_manifest

        # NOTE: We use the DockerSchema1ManifestBuilder here because it already contains
        # the logic for generating the DockerV1Metadata. All of this will go away once we get
        # rid of legacy images in the database, so this is a temporary solution.
        v1_builder = DockerSchema1ManifestBuilder("", "", "")
        self._populate_schema1_builder(v1_builder, content_retriever)
        return v1_builder.build().generate_legacy_layers(images_map, content_retriever)

    def get_leaf_layer_v1_image_id(self, content_retriever):
        # NOTE: If there exists a layer with remote content, then we consider this manifest
        # to not support legacy images.
        if self.has_remote_layer or not self.is_image_manifest:
            return None

        return self.get_legacy_image_ids(content_retriever)[-1].v1_id

    def get_legacy_image_ids(self, content_retriever):
        if self.has_remote_layer or not self.is_image_manifest:
            return None

        return [l.v1_id for l in self._manifest_image_layers(content_retriever)]

    def convert_manifest(
        self, allowed_mediatypes, namespace_name, repo_name, tag_name, content_retriever
    ):
        if self.media_type in allowed_mediatypes:
            return self

        if not self.is_image_manifest:
            return None

        # If this manifest is not on the allowed list, try to convert the schema 1 version (if any)
        schema1 = self.get_schema1_manifest(namespace_name, repo_name, tag_name, content_retriever)
        if schema1 is None:
            return None

        return schema1.convert_manifest(
            allowed_mediatypes, namespace_name, repo_name, tag_name, content_retriever
        )

    def get_schema1_manifest(self, namespace_name, repo_name, tag_name, content_retriever):
        if self.has_remote_layer or not self.is_image_manifest:
            return None

        v1_builder = DockerSchema1ManifestBuilder(namespace_name, repo_name, tag_name)
        self._populate_schema1_builder(v1_builder, content_retriever)
        return v1_builder.build()

    def unsigned(self):
        return self

    def get_requires_empty_layer_blob(self, content_retriever):
        if not self.is_image_manifest:
            return False

        schema2_config = self._get_built_config(content_retriever)
        if schema2_config is None:
            return None

        return schema2_config.has_empty_layer

    def _populate_schema1_builder(self, v1_builder, content_retriever):
        """
        Populates a DockerSchema1ManifestBuilder with the layers and config from this schema.
        """
        assert not self.has_remote_layer
        assert self.is_image_manifest

        schema2_config = self._get_built_config(content_retriever)
        layers = list(self._manifest_image_layers(content_retriever))

        for index, layer in enumerate(reversed(layers)):  # Schema 1 layers are in reverse order
            v1_compatibility = schema2_config.build_v1_compatibility(
                layer.history, layer.v1_id, layer.v1_parent_id, index == 0, layer.compressed_size
            )
            v1_builder.add_layer(str(layer.blob_digest), json.dumps(v1_compatibility))

        return v1_builder

    def _get_built_config(self, content_retriever):
        assert self.is_image_manifest

        if self._cached_built_config:
            return self._cached_built_config

        config_bytes = content_retriever.get_blob_bytes_with_digest(self.config.digest)
        if config_bytes is None:
            raise MalformedOCIManifest("Could not load config blob for manifest")

        if len(config_bytes) != self.config.size:
            msg = "Size of config does not match that retrieved: %s vs %s" % (
                len(config_bytes),
                self.config.size,
            )
            raise MalformedOCIManifest(msg)

        self._cached_built_config = OCIConfig(Bytes.for_string_or_unicode(config_bytes))
        return self._cached_built_config

    def _generate_filesystem_layers(self):
        for index, layer in enumerate(self._parsed[OCI_MANIFEST_LAYERS_KEY]):
            content_type = layer[OCI_MANIFEST_MEDIATYPE_KEY]
            is_remote = content_type in OCI_IMAGE_NON_DISTRIBUTABLE_LAYER_CONTENT_TYPES

            try:
                digest = digest_tools.Digest.parse_digest(layer[OCI_MANIFEST_DIGEST_KEY])
            except digest_tools.InvalidDigestException:
                raise MalformedOCIManifest(
                    "could not parse manifest digest: %s" % layer[OCI_MANIFEST_DIGEST_KEY]
                )

            yield OCIManifestLayer(
                index=index,
                compressed_size=layer[OCI_MANIFEST_SIZE_KEY],
                digest=digest,
                is_remote=is_remote,
                urls=layer.get(OCI_MANIFEST_URLS_KEY),
            )


class OCIManifestBuilder(object):
    """
    A convenient abstraction around creating new OCIManifest.
    """

    def __init__(self):
        self.config = None
        self.filesystem_layers = []

    def clone(self):
        cloned = OCIManifestBuilder()
        cloned.config = self.config
        cloned.filesystem_layers = list(self.filesystem_layers)
        return cloned

    def set_config(self, schema2_config):
        """
        Sets the configuration for the manifest being built.
        """
        self.set_config_digest(schema2_config.digest, schema2_config.size)

    def set_config_digest(self, config_digest, config_size):
        """
        Sets the digest and size of the configuration layer.
        """
        self.config = OCIManifestConfig(size=config_size, digest=config_digest)

    def add_layer(self, digest, size, urls=None):
        """
        Adds a filesystem layer to the manifest.
        """
        self.filesystem_layers.append(
            OCIManifestLayer(
                index=len(self.filesystem_layers),
                digest=digest,
                compressed_size=size,
                urls=urls,
                is_remote=bool(urls),
            )
        )

    def build(self, ensure_ascii=True):
        """
        Builds and returns the OCIManifest.
        """
        assert self.filesystem_layers
        assert self.config

        def _build_layer(layer):
            if layer.urls:
                return {
                    OCI_MANIFEST_MEDIATYPE_KEY: OCI_IMAGE_TAR_GZIP_NON_DISTRIBUTABLE_LAYER_CONTENT_TYPE,
                    OCI_MANIFEST_SIZE_KEY: layer.compressed_size,
                    OCI_MANIFEST_DIGEST_KEY: str(layer.digest),
                    OCI_MANIFEST_URLS_KEY: layer.urls,
                }

            return {
                OCI_MANIFEST_MEDIATYPE_KEY: OCI_IMAGE_TAR_GZIP_LAYER_CONTENT_TYPE,
                OCI_MANIFEST_SIZE_KEY: layer.compressed_size,
                OCI_MANIFEST_DIGEST_KEY: str(layer.digest),
            }

        manifest_dict = {
            OCI_MANIFEST_VERSION_KEY: 2,
            OCI_MANIFEST_MEDIATYPE_KEY: OCI_IMAGE_MANIFEST_CONTENT_TYPE,
            # Config
            OCI_MANIFEST_CONFIG_KEY: {
                OCI_MANIFEST_MEDIATYPE_KEY: OCI_IMAGE_CONFIG_CONTENT_TYPE,
                OCI_MANIFEST_SIZE_KEY: self.config.size,
                OCI_MANIFEST_DIGEST_KEY: str(self.config.digest),
            },
            # Layers
            OCI_MANIFEST_LAYERS_KEY: [_build_layer(layer) for layer in self.filesystem_layers],
        }

        json_str = json.dumps(manifest_dict, ensure_ascii=ensure_ascii, indent=3)
        return OCIManifest(Bytes.for_string_or_unicode(json_str))
