import json
import logging
import hashlib

from collections import namedtuple
from jsonschema import validate as validate_schema, ValidationError

from digest import digest_tools
from image.shared import ManifestException
from image.shared.interfaces import ManifestInterface
from image.shared.types import ManifestImageLayer
from image.docker.schema2 import (
    DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA2_CONFIG_CONTENT_TYPE,
    DOCKER_SCHEMA2_LAYER_CONTENT_TYPE,
    DOCKER_SCHEMA2_REMOTE_LAYER_CONTENT_TYPE,
    EMPTY_LAYER_BLOB_DIGEST,
    EMPTY_LAYER_SIZE,
)
from image.docker.schema1 import DockerSchema1ManifestBuilder
from image.docker.schema2.config import DockerSchema2Config
from util.bytes import Bytes

# Keys.
DOCKER_SCHEMA2_MANIFEST_VERSION_KEY = "schemaVersion"
DOCKER_SCHEMA2_MANIFEST_MEDIATYPE_KEY = "mediaType"
DOCKER_SCHEMA2_MANIFEST_CONFIG_KEY = "config"
DOCKER_SCHEMA2_MANIFEST_SIZE_KEY = "size"
DOCKER_SCHEMA2_MANIFEST_DIGEST_KEY = "digest"
DOCKER_SCHEMA2_MANIFEST_LAYERS_KEY = "layers"
DOCKER_SCHEMA2_MANIFEST_URLS_KEY = "urls"

# Named tuples.
DockerV2ManifestConfig = namedtuple("DockerV2ManifestConfig", ["size", "digest"])
DockerV2ManifestLayer = namedtuple(
    "DockerV2ManifestLayer", ["index", "digest", "is_remote", "urls", "compressed_size"]
)

DockerV2ManifestImageLayer = namedtuple(
    "DockerV2ManifestImageLayer",
    ["history", "blob_layer", "v1_id", "v1_parent_id", "compressed_size", "blob_digest"],
)

logger = logging.getLogger(__name__)


class MalformedSchema2Manifest(ManifestException):
    """
    Raised when a manifest fails an assertion that should be true according to the Docker Manifest
    v2.2 Specification.
    """

    pass


class DockerSchema2Manifest(ManifestInterface):
    METASCHEMA = {
        "type": "object",
        "properties": {
            DOCKER_SCHEMA2_MANIFEST_VERSION_KEY: {
                "type": "number",
                "description": "The version of the schema. Must always be `2`.",
                "minimum": 2,
                "maximum": 2,
            },
            DOCKER_SCHEMA2_MANIFEST_MEDIATYPE_KEY: {
                "type": "string",
                "description": "The media type of the schema.",
                "enum": [DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE],
            },
            DOCKER_SCHEMA2_MANIFEST_CONFIG_KEY: {
                "type": "object",
                "description": "The config field references a configuration object for a container, "
                + "by digest. This configuration item is a JSON blob that the runtime "
                + "uses to set up the container.",
                "properties": {
                    DOCKER_SCHEMA2_MANIFEST_MEDIATYPE_KEY: {
                        "type": "string",
                        "description": "The MIME type of the referenced object. This should generally be "
                        + "application/vnd.docker.container.image.v1+json",
                        "enum": [DOCKER_SCHEMA2_CONFIG_CONTENT_TYPE],
                    },
                    DOCKER_SCHEMA2_MANIFEST_SIZE_KEY: {
                        "type": "number",
                        "description": "The size in bytes of the object. This field exists so that a "
                        + "client will have an expected size for the content before "
                        + "validating. If the length of the retrieved content does not "
                        + "match the specified length, the content should not be trusted.",
                    },
                    DOCKER_SCHEMA2_MANIFEST_DIGEST_KEY: {
                        "type": "string",
                        "description": "The content addressable digest of the config in the blob store",
                    },
                },
                "required": [
                    DOCKER_SCHEMA2_MANIFEST_MEDIATYPE_KEY,
                    DOCKER_SCHEMA2_MANIFEST_SIZE_KEY,
                    DOCKER_SCHEMA2_MANIFEST_DIGEST_KEY,
                ],
            },
            DOCKER_SCHEMA2_MANIFEST_LAYERS_KEY: {
                "type": "array",
                "description": "The layer list is ordered starting from the base "
                + "image (opposite order of schema1).",
                "items": {
                    "type": "object",
                    "properties": {
                        DOCKER_SCHEMA2_MANIFEST_MEDIATYPE_KEY: {
                            "type": "string",
                            "description": "The MIME type of the referenced object. This should generally be "
                            + "application/vnd.docker.image.rootfs.diff.tar.gzip. Layers of type "
                            + "application/vnd.docker.image.rootfs.foreign.diff.tar.gzip may be "
                            + "pulled from a remote location but they should never be pushed.",
                            "enum": [
                                DOCKER_SCHEMA2_LAYER_CONTENT_TYPE,
                                DOCKER_SCHEMA2_REMOTE_LAYER_CONTENT_TYPE,
                            ],
                        },
                        DOCKER_SCHEMA2_MANIFEST_SIZE_KEY: {
                            "type": "number",
                            "description": "The size in bytes of the object. This field exists so that a "
                            + "client will have an expected size for the content before "
                            + "validating. If the length of the retrieved content does not "
                            + "match the specified length, the content should not be trusted.",
                        },
                        DOCKER_SCHEMA2_MANIFEST_DIGEST_KEY: {
                            "type": "string",
                            "description": "The content addressable digest of the layer in the blob store",
                        },
                    },
                    "required": [
                        DOCKER_SCHEMA2_MANIFEST_MEDIATYPE_KEY,
                        DOCKER_SCHEMA2_MANIFEST_SIZE_KEY,
                        DOCKER_SCHEMA2_MANIFEST_DIGEST_KEY,
                    ],
                },
            },
        },
        "required": [
            DOCKER_SCHEMA2_MANIFEST_VERSION_KEY,
            DOCKER_SCHEMA2_MANIFEST_MEDIATYPE_KEY,
            DOCKER_SCHEMA2_MANIFEST_CONFIG_KEY,
            DOCKER_SCHEMA2_MANIFEST_LAYERS_KEY,
        ],
    }

    def __init__(self, manifest_bytes, validate=False):
        assert isinstance(manifest_bytes, Bytes)

        self._payload = manifest_bytes

        self._filesystem_layers = None
        self._cached_built_config = None

        try:
            self._parsed = json.loads(self._payload.as_unicode())
        except ValueError as ve:
            raise MalformedSchema2Manifest("malformed manifest data: %s" % ve)

        try:
            validate_schema(self._parsed, DockerSchema2Manifest.METASCHEMA)
        except ValidationError as ve:
            raise MalformedSchema2Manifest("manifest data does not match schema: %s" % ve)

        for layer in self.filesystem_layers:
            if layer.is_remote and not layer.urls:
                raise MalformedSchema2Manifest("missing `urls` for remote layer")

    def validate(self, content_retriever):
        """
        Performs validation of required assertions about the manifest.

        Raises a ManifestException on failure.
        """
        self._get_built_config(content_retriever)

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
        return self._parsed[DOCKER_SCHEMA2_MANIFEST_MEDIATYPE_KEY]

    @property
    def digest(self):
        return digest_tools.sha256_digest(self._payload.as_encoded_str())

    @property
    def config(self):
        config = self._parsed[DOCKER_SCHEMA2_MANIFEST_CONFIG_KEY]
        return DockerV2ManifestConfig(
            size=config[DOCKER_SCHEMA2_MANIFEST_SIZE_KEY],
            digest=config[DOCKER_SCHEMA2_MANIFEST_DIGEST_KEY],
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
    def layers_compressed_size(self):
        return sum(layer.compressed_size for layer in self.filesystem_layers)

    @property
    def config_media_type(self):
        return self._parsed[DOCKER_SCHEMA2_MANIFEST_CONFIG_KEY][
            DOCKER_SCHEMA2_MANIFEST_MEDIATYPE_KEY
        ]

    @property
    def has_remote_layer(self):
        for layer in self.filesystem_layers:
            if layer.is_remote:
                return True

        return False

    @property
    def blob_digests(self):
        return [str(layer.digest) for layer in self.filesystem_layers] + [str(self.config.digest)]

    @property
    def local_blob_digests(self):
        return [str(layer.digest) for layer in self.filesystem_layers if not layer.urls] + [
            str(self.config.digest)
        ]

    def get_blob_digests_for_translation(self):
        return self.blob_digests

    def get_manifest_labels(self, content_retriever):
        return self._get_built_config(content_retriever).labels

    def get_layers(self, content_retriever):
        """
        Returns the layers of this manifest, from base to leaf or None if this kind of manifest does
        not support layers.
        """
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
        # Retrieve the configuration for the manifest.
        config = self._get_built_config(content_retriever)
        history = list(config.history)
        if len(history) < len(self.filesystem_layers):
            raise MalformedSchema2Manifest("Found less history than layer blobs")

        digest_history = hashlib.sha256()
        v1_layer_parent_id = None
        v1_layer_id = None
        blob_index = 0

        for history_index, history_entry in enumerate(history):
            if not history_entry.is_empty and blob_index >= len(self.filesystem_layers):
                raise MalformedSchema2Manifest("Missing history entry #%s" % blob_index)

            v1_layer_parent_id = v1_layer_id
            blob_layer = None if history_entry.is_empty else self.filesystem_layers[blob_index]
            blob_digest = EMPTY_LAYER_BLOB_DIGEST if blob_layer is None else str(blob_layer.digest)
            compressed_size = EMPTY_LAYER_SIZE if blob_layer is None else blob_layer.compressed_size

            # Create a new synthesized V1 ID for the history layer by hashing its content and
            # the blob associated with it.
            digest_history.update(json.dumps(history_entry.raw_entry).encode("utf-8") or b"empty")
            digest_history.update("|".encode("utf-8"))
            digest_history.update(str(history_index).encode("utf-8"))
            digest_history.update("|".encode("utf-8"))
            digest_history.update(blob_digest.encode("utf-8"))
            digest_history.update("||".encode("utf-8"))

            v1_layer_id = digest_history.hexdigest()
            yield DockerV2ManifestImageLayer(
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
        """ Returns whether this manifest is empty. """
        return len(self._parsed[DOCKER_SCHEMA2_MANIFEST_LAYERS_KEY]) == 0

    @property
    def has_legacy_image(self):
        return not self.has_remote_layer and not self.is_empty_manifest

    def generate_legacy_layers(self, images_map, content_retriever):
        assert not self.has_remote_layer

        # NOTE: We use the DockerSchema1ManifestBuilder here because it already contains
        # the logic for generating the DockerV1Metadata. All of this will go away once we get
        # rid of legacy images in the database, so this is a temporary solution.
        v1_builder = DockerSchema1ManifestBuilder("", "", "")
        self._populate_schema1_builder(v1_builder, content_retriever)
        return v1_builder.build().generate_legacy_layers(images_map, content_retriever)

    def get_leaf_layer_v1_image_id(self, content_retriever):
        # NOTE: If there exists a layer with remote content, then we consider this manifest
        # to not support legacy images.
        if self.has_remote_layer:
            return None

        return self.get_legacy_image_ids(content_retriever)[-1].v1_id

    def get_legacy_image_ids(self, content_retriever):
        if self.has_remote_layer:
            return None

        return [l.v1_id for l in self._manifest_image_layers(content_retriever)]

    def convert_manifest(
        self, allowed_mediatypes, namespace_name, repo_name, tag_name, content_retriever
    ):
        if self.media_type in allowed_mediatypes:
            return self

        # If this manifest is not on the allowed list, try to convert the schema 1 version (if any)
        schema1 = self.get_schema1_manifest(namespace_name, repo_name, tag_name, content_retriever)
        if schema1 is None:
            return None

        return schema1.convert_manifest(
            allowed_mediatypes, namespace_name, repo_name, tag_name, content_retriever
        )

    def get_schema1_manifest(self, namespace_name, repo_name, tag_name, content_retriever):
        if self.has_remote_layer:
            return None

        v1_builder = DockerSchema1ManifestBuilder(namespace_name, repo_name, tag_name)
        self._populate_schema1_builder(v1_builder, content_retriever)
        return v1_builder.build()

    def unsigned(self):
        return self

    def get_requires_empty_layer_blob(self, content_retriever):
        schema2_config = self._get_built_config(content_retriever)
        if schema2_config is None:
            return None

        return schema2_config.has_empty_layer

    def _populate_schema1_builder(self, v1_builder, content_retriever):
        """
        Populates a DockerSchema1ManifestBuilder with the layers and config from this schema.
        """
        assert not self.has_remote_layer
        schema2_config = self._get_built_config(content_retriever)
        layers = list(self._manifest_image_layers(content_retriever))

        for index, layer in enumerate(reversed(layers)):  # Schema 1 layers are in reverse order
            v1_compatibility = schema2_config.build_v1_compatibility(
                layer.history, layer.v1_id, layer.v1_parent_id, index == 0, layer.compressed_size
            )
            v1_builder.add_layer(str(layer.blob_digest), json.dumps(v1_compatibility))

        return v1_builder

    def _get_built_config(self, content_retriever):
        if self._cached_built_config:
            return self._cached_built_config

        config_bytes = content_retriever.get_blob_bytes_with_digest(self.config.digest)
        if config_bytes is None:
            raise MalformedSchema2Manifest("Could not load config blob for manifest")

        if len(config_bytes) != self.config.size:
            msg = "Size of config does not match that retrieved: %s vs %s" % (
                len(config_bytes),
                self.config.size,
            )
            raise MalformedSchema2Manifest(msg)

        self._cached_built_config = DockerSchema2Config(Bytes.for_string_or_unicode(config_bytes))
        return self._cached_built_config

    def _generate_filesystem_layers(self):
        for index, layer in enumerate(self._parsed[DOCKER_SCHEMA2_MANIFEST_LAYERS_KEY]):
            content_type = layer[DOCKER_SCHEMA2_MANIFEST_MEDIATYPE_KEY]
            is_remote = content_type == DOCKER_SCHEMA2_REMOTE_LAYER_CONTENT_TYPE

            try:
                digest = digest_tools.Digest.parse_digest(layer[DOCKER_SCHEMA2_MANIFEST_DIGEST_KEY])
            except digest_tools.InvalidDigestException:
                raise MalformedSchema2Manifest(
                    "could not parse manifest digest: %s"
                    % layer[DOCKER_SCHEMA2_MANIFEST_DIGEST_KEY]
                )

            yield DockerV2ManifestLayer(
                index=index,
                compressed_size=layer[DOCKER_SCHEMA2_MANIFEST_SIZE_KEY],
                digest=digest,
                is_remote=is_remote,
                urls=layer.get(DOCKER_SCHEMA2_MANIFEST_URLS_KEY),
            )


class DockerSchema2ManifestBuilder(object):
    """
    A convenient abstraction around creating new DockerSchema2Manifests.
    """

    def __init__(self):
        self.config = None
        self.filesystem_layers = []

    def clone(self):
        cloned = DockerSchema2ManifestBuilder()
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
        self.config = DockerV2ManifestConfig(size=config_size, digest=config_digest)

    def add_layer(self, digest, size, urls=None):
        """
        Adds a filesystem layer to the manifest.
        """
        self.filesystem_layers.append(
            DockerV2ManifestLayer(
                index=len(self.filesystem_layers),
                digest=digest,
                compressed_size=size,
                urls=urls,
                is_remote=bool(urls),
            )
        )

    def build(self, ensure_ascii=True):
        """
        Builds and returns the DockerSchema2Manifest.
        """
        assert self.config

        def _build_layer(layer):
            if layer.urls:
                return {
                    DOCKER_SCHEMA2_MANIFEST_MEDIATYPE_KEY: DOCKER_SCHEMA2_REMOTE_LAYER_CONTENT_TYPE,
                    DOCKER_SCHEMA2_MANIFEST_SIZE_KEY: layer.compressed_size,
                    DOCKER_SCHEMA2_MANIFEST_DIGEST_KEY: str(layer.digest),
                    DOCKER_SCHEMA2_MANIFEST_URLS_KEY: layer.urls,
                }

            return {
                DOCKER_SCHEMA2_MANIFEST_MEDIATYPE_KEY: DOCKER_SCHEMA2_LAYER_CONTENT_TYPE,
                DOCKER_SCHEMA2_MANIFEST_SIZE_KEY: layer.compressed_size,
                DOCKER_SCHEMA2_MANIFEST_DIGEST_KEY: str(layer.digest),
            }

        manifest_dict = {
            DOCKER_SCHEMA2_MANIFEST_VERSION_KEY: 2,
            DOCKER_SCHEMA2_MANIFEST_MEDIATYPE_KEY: DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
            # Config
            DOCKER_SCHEMA2_MANIFEST_CONFIG_KEY: {
                DOCKER_SCHEMA2_MANIFEST_MEDIATYPE_KEY: DOCKER_SCHEMA2_CONFIG_CONTENT_TYPE,
                DOCKER_SCHEMA2_MANIFEST_SIZE_KEY: self.config.size,
                DOCKER_SCHEMA2_MANIFEST_DIGEST_KEY: str(self.config.digest),
            },
            # Layers
            DOCKER_SCHEMA2_MANIFEST_LAYERS_KEY: [
                _build_layer(layer) for layer in self.filesystem_layers
            ],
        }

        json_str = json.dumps(manifest_dict, ensure_ascii=ensure_ascii, indent=3)
        return DockerSchema2Manifest(Bytes.for_string_or_unicode(json_str))
