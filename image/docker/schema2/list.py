import logging
import json

from cachetools.func import lru_cache
from jsonschema import validate as validate_schema, ValidationError

from digest import digest_tools
from image.shared import ManifestException
from image.shared.interfaces import ManifestListInterface
from image.shared.schemautil import LazyManifestLoader
from image.docker.schema1 import DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE
from image.docker.schema1 import DockerSchema1Manifest
from image.docker.schema2 import (
    DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
    DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
)
from image.docker.schema2.manifest import DockerSchema2Manifest
from util.bytes import Bytes


logger = logging.getLogger(__name__)

# Keys.
DOCKER_SCHEMA2_MANIFESTLIST_VERSION_KEY = "schemaVersion"
DOCKER_SCHEMA2_MANIFESTLIST_MEDIATYPE_KEY = "mediaType"
DOCKER_SCHEMA2_MANIFESTLIST_SIZE_KEY = "size"
DOCKER_SCHEMA2_MANIFESTLIST_DIGEST_KEY = "digest"
DOCKER_SCHEMA2_MANIFESTLIST_MANIFESTS_KEY = "manifests"
DOCKER_SCHEMA2_MANIFESTLIST_PLATFORM_KEY = "platform"
DOCKER_SCHEMA2_MANIFESTLIST_ARCHITECTURE_KEY = "architecture"
DOCKER_SCHEMA2_MANIFESTLIST_OS_KEY = "os"
DOCKER_SCHEMA2_MANIFESTLIST_OS_VERSION_KEY = "os.version"
DOCKER_SCHEMA2_MANIFESTLIST_OS_FEATURES_KEY = "os.features"
DOCKER_SCHEMA2_MANIFESTLIST_FEATURES_KEY = "features"
DOCKER_SCHEMA2_MANIFESTLIST_VARIANT_KEY = "variant"


class MalformedSchema2ManifestList(ManifestException):
    """
    Raised when a manifest list fails an assertion that should be true according to the Docker
    Manifest v2.2 Specification.
    """

    pass


class MismatchManifestException(MalformedSchema2ManifestList):
    """
    Raised when a manifest list contains a schema 1 manifest with a differing architecture from that
    specified in the manifest list for the manifest.
    """

    pass


class DockerSchema2ManifestList(ManifestListInterface):
    METASCHEMA = {
        "type": "object",
        "properties": {
            DOCKER_SCHEMA2_MANIFESTLIST_VERSION_KEY: {
                "type": "number",
                "description": "The version of the manifest list. Must always be `2`.",
                "minimum": 2,
                "maximum": 2,
            },
            DOCKER_SCHEMA2_MANIFESTLIST_MEDIATYPE_KEY: {
                "type": "string",
                "description": "The media type of the manifest list.",
                "enum": [DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE],
            },
            DOCKER_SCHEMA2_MANIFESTLIST_MANIFESTS_KEY: {
                "type": "array",
                "description": "The manifests field contains a list of manifests for specific platforms",
                "items": {
                    "type": "object",
                    "properties": {
                        DOCKER_SCHEMA2_MANIFESTLIST_MEDIATYPE_KEY: {
                            "type": "string",
                            "description": "The MIME type of the referenced object. This will generally be "
                            + "application/vnd.docker.distribution.manifest.v2+json, but it "
                            + "could also be application/vnd.docker.distribution.manifest.v1+json "
                            + "if the manifest list references a legacy schema-1 manifest.",
                            "enum": [
                                DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
                                DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE,
                            ],
                        },
                        DOCKER_SCHEMA2_MANIFESTLIST_SIZE_KEY: {
                            "type": "number",
                            "description": "The size in bytes of the object. This field exists so that a "
                            + "client will have an expected size for the content before "
                            + "validating. If the length of the retrieved content does not "
                            + "match the specified length, the content should not be trusted.",
                        },
                        DOCKER_SCHEMA2_MANIFESTLIST_DIGEST_KEY: {
                            "type": "string",
                            "description": "The content addressable digest of the manifest in the blob store",
                        },
                        DOCKER_SCHEMA2_MANIFESTLIST_PLATFORM_KEY: {
                            "type": "object",
                            "description": "The platform object describes the platform which the image in "
                            + "the manifest runs on",
                            "properties": {
                                DOCKER_SCHEMA2_MANIFESTLIST_ARCHITECTURE_KEY: {
                                    "type": "string",
                                    "description": "Specifies the CPU architecture, for example amd64 or ppc64le.",
                                },
                                DOCKER_SCHEMA2_MANIFESTLIST_OS_KEY: {
                                    "type": "string",
                                    "description": "Specifies the operating system, for example linux or windows",
                                },
                                DOCKER_SCHEMA2_MANIFESTLIST_OS_VERSION_KEY: {
                                    "type": "string",
                                    "description": "Specifies the operating system version, for example 10.0.10586",
                                },
                                DOCKER_SCHEMA2_MANIFESTLIST_OS_FEATURES_KEY: {
                                    "type": "array",
                                    "description": "specifies an array of strings, each listing a required OS "
                                    + "feature (for example on Windows win32k)",
                                    "items": {"type": "string",},
                                },
                                DOCKER_SCHEMA2_MANIFESTLIST_VARIANT_KEY: {
                                    "type": "string",
                                    "description": "Specifies a variant of the CPU, for example armv6l to specify "
                                    + "a particular CPU variant of the ARM CPU",
                                },
                                DOCKER_SCHEMA2_MANIFESTLIST_FEATURES_KEY: {
                                    "type": "array",
                                    "description": "specifies an array of strings, each listing a required CPU "
                                    + "feature (for example sse4 or aes).",
                                    "items": {"type": "string",},
                                },
                            },
                            "required": [
                                DOCKER_SCHEMA2_MANIFESTLIST_ARCHITECTURE_KEY,
                                DOCKER_SCHEMA2_MANIFESTLIST_OS_KEY,
                            ],
                        },
                    },
                    "required": [
                        DOCKER_SCHEMA2_MANIFESTLIST_MEDIATYPE_KEY,
                        DOCKER_SCHEMA2_MANIFESTLIST_SIZE_KEY,
                        DOCKER_SCHEMA2_MANIFESTLIST_DIGEST_KEY,
                        DOCKER_SCHEMA2_MANIFESTLIST_PLATFORM_KEY,
                    ],
                },
            },
        },
        "required": [
            DOCKER_SCHEMA2_MANIFESTLIST_VERSION_KEY,
            DOCKER_SCHEMA2_MANIFESTLIST_MEDIATYPE_KEY,
            DOCKER_SCHEMA2_MANIFESTLIST_MANIFESTS_KEY,
        ],
    }

    def __init__(self, manifest_bytes):
        assert isinstance(manifest_bytes, Bytes)

        self._layers = None
        self._manifest_bytes = manifest_bytes

        try:
            self._parsed = json.loads(manifest_bytes.as_unicode())
        except ValueError as ve:
            raise MalformedSchema2ManifestList("malformed manifest data: %s" % ve)

        try:
            validate_schema(self._parsed, DockerSchema2ManifestList.METASCHEMA)
        except ValidationError as ve:
            raise MalformedSchema2ManifestList("manifest data does not match schema: %s" % ve)

    @property
    def is_manifest_list(self):
        """
        Returns whether this manifest is a list.
        """
        return True

    @property
    def schema_version(self):
        return 2

    @property
    def digest(self):
        """
        The digest of the manifest, including type prefix.
        """
        return digest_tools.sha256_digest(self._manifest_bytes.as_encoded_str())

    @property
    def media_type(self):
        """
        The media type of the schema.
        """
        return self._parsed[DOCKER_SCHEMA2_MANIFESTLIST_MEDIATYPE_KEY]

    @property
    def manifest_dict(self):
        """
        Returns the manifest as a dictionary ready to be serialized to JSON.
        """
        return self._parsed

    @property
    def bytes(self):
        return self._manifest_bytes

    def get_layers(self, content_retriever):
        """
        Returns the layers of this manifest, from base to leaf or None if this kind of manifest does
        not support layers.
        """
        return None

    @property
    def blob_digests(self):
        # Manifest lists have no blob digests, since everything is stored as a manifest.
        return []

    @property
    def local_blob_digests(self):
        return self.blob_digests

    def get_blob_digests_for_translation(self):
        return self.blob_digests

    @property
    def layers_compressed_size(self):
        return None

    @property
    def config_media_type(self):
        return None

    @lru_cache(maxsize=1)
    def manifests(self, content_retriever):
        """
        Returns the manifests in the list.
        """
        manifests = self._parsed[DOCKER_SCHEMA2_MANIFESTLIST_MANIFESTS_KEY]
        supported_types = {}
        supported_types[DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE] = DockerSchema1Manifest
        supported_types[DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE] = DockerSchema2Manifest
        return [
            LazyManifestLoader(
                m,
                content_retriever,
                supported_types,
                DOCKER_SCHEMA2_MANIFESTLIST_DIGEST_KEY,
                DOCKER_SCHEMA2_MANIFESTLIST_SIZE_KEY,
                DOCKER_SCHEMA2_MANIFESTLIST_MEDIATYPE_KEY,
            )
            for m in manifests
        ]

    @property
    def amd64_linux_manifest_digest(self):
        """ Returns the digest of the AMD64+Linux manifest in this list, if any, or None
            if none.
        """
        for manifest_ref in self._parsed[DOCKER_SCHEMA2_MANIFESTLIST_MANIFESTS_KEY]:
            platform = manifest_ref[DOCKER_SCHEMA2_MANIFESTLIST_PLATFORM_KEY]
            architecture = platform[DOCKER_SCHEMA2_MANIFESTLIST_ARCHITECTURE_KEY]
            os = platform[DOCKER_SCHEMA2_MANIFESTLIST_OS_KEY]
            if architecture == "amd64" and os == "linux":
                return manifest_ref[DOCKER_SCHEMA2_MANIFESTLIST_DIGEST_KEY]

        return None

    def validate(self, content_retriever):
        """
        Performs validation of required assertions about the manifest.

        Raises a ManifestException on failure.
        """
        for index, m in enumerate(self._parsed[DOCKER_SCHEMA2_MANIFESTLIST_MANIFESTS_KEY]):
            if m[DOCKER_SCHEMA2_MANIFESTLIST_MEDIATYPE_KEY] == DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE:
                platform = m[DOCKER_SCHEMA2_MANIFESTLIST_PLATFORM_KEY]

                # Validate the architecture against the schema 1 architecture defined.
                parsed = self.manifests(content_retriever)[index].manifest_obj
                assert isinstance(parsed, DockerSchema1Manifest)
                if (
                    parsed.architecture
                    and parsed.architecture
                    != platform[DOCKER_SCHEMA2_MANIFESTLIST_ARCHITECTURE_KEY]
                ):
                    raise MismatchManifestException(
                        "Mismatch in arch for manifest `%s`" % parsed.digest
                    )

    def child_manifests(self, content_retriever):
        return self.manifests(content_retriever)

    def child_manifest_digests(self):
        return [
            m[DOCKER_SCHEMA2_MANIFESTLIST_DIGEST_KEY]
            for m in self._parsed[DOCKER_SCHEMA2_MANIFESTLIST_MANIFESTS_KEY]
        ]

    def get_manifest_labels(self, content_retriever):
        return None

    def get_leaf_layer_v1_image_id(self, content_retriever):
        return None

    def get_legacy_image_ids(self, content_retriever):
        return None

    @property
    def has_legacy_image(self):
        return False

    def get_requires_empty_layer_blob(self, content_retriever):
        return False

    def get_schema1_manifest(self, namespace_name, repo_name, tag_name, content_retriever):
        """
        Returns the manifest that is compatible with V1, by virtue of being `amd64` and `linux`.

        If none, returns None.
        """
        legacy_manifest = self._get_legacy_manifest(content_retriever)
        if legacy_manifest is None:
            return None

        return legacy_manifest.get_schema1_manifest(
            namespace_name, repo_name, tag_name, content_retriever
        )

    def convert_manifest(
        self, allowed_mediatypes, namespace_name, repo_name, tag_name, content_retriever
    ):
        if self.media_type in allowed_mediatypes:
            return self

        legacy_manifest = self._get_legacy_manifest(content_retriever)
        if legacy_manifest is None:
            return None

        return legacy_manifest.convert_manifest(
            allowed_mediatypes, namespace_name, repo_name, tag_name, content_retriever
        )

    def _get_legacy_manifest(self, content_retriever):
        """
        Returns the manifest under this list with architecture amd64 and os linux, if any, or None
        if none or error.
        """
        for manifest_ref in self.manifests(content_retriever):
            platform = manifest_ref._manifest_data[DOCKER_SCHEMA2_MANIFESTLIST_PLATFORM_KEY]
            architecture = platform[DOCKER_SCHEMA2_MANIFESTLIST_ARCHITECTURE_KEY]
            os = platform[DOCKER_SCHEMA2_MANIFESTLIST_OS_KEY]
            if architecture != "amd64" or os != "linux":
                continue

            try:
                return manifest_ref.manifest_obj
            except (ManifestException, IOError):
                logger.exception("Could not load child manifest")
                return None

        return None

    def unsigned(self):
        return self

    def generate_legacy_layers(self, images_map, content_retriever):
        return None


class DockerSchema2ManifestListBuilder(object):
    """
    A convenient abstraction around creating new DockerSchema2ManifestList's.
    """

    def __init__(self):
        self.manifests = []

    def add_manifest(self, manifest, architecture, os):
        """
        Adds a manifest to the list.
        """
        manifest = manifest.unsigned()  # Make sure we add the unsigned version to the list.
        self.add_manifest_digest(
            manifest.digest,
            len(manifest.bytes.as_encoded_str()),
            manifest.media_type,
            architecture,
            os,
        )

    def add_manifest_digest(self, manifest_digest, manifest_size, media_type, architecture, os):
        """
        Adds a manifest to the list.
        """
        self.manifests.append(
            (
                manifest_digest,
                manifest_size,
                media_type,
                {
                    DOCKER_SCHEMA2_MANIFESTLIST_ARCHITECTURE_KEY: architecture,
                    DOCKER_SCHEMA2_MANIFESTLIST_OS_KEY: os,
                },
            )
        )

    def build(self):
        """
        Builds and returns the DockerSchema2ManifestList.
        """
        assert self.manifests

        manifest_list_dict = {
            DOCKER_SCHEMA2_MANIFESTLIST_VERSION_KEY: 2,
            DOCKER_SCHEMA2_MANIFESTLIST_MEDIATYPE_KEY: DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
            DOCKER_SCHEMA2_MANIFESTLIST_MANIFESTS_KEY: [
                {
                    DOCKER_SCHEMA2_MANIFESTLIST_MEDIATYPE_KEY: manifest[2],
                    DOCKER_SCHEMA2_MANIFESTLIST_DIGEST_KEY: manifest[0],
                    DOCKER_SCHEMA2_MANIFESTLIST_SIZE_KEY: manifest[1],
                    DOCKER_SCHEMA2_MANIFESTLIST_PLATFORM_KEY: manifest[3],
                }
                for manifest in self.manifests
            ],
        }

        json_str = Bytes.for_string_or_unicode(json.dumps(manifest_list_dict, indent=3))
        return DockerSchema2ManifestList(json_str)
