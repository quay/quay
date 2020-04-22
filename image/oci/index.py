"""
Implements validation and conversion for the OCI Index JSON.

See: https://github.com/opencontainers/image-spec/blob/master/image-index.md

Example:
{
  "schemaVersion": 2,
  "manifests": [
    {
      "mediaType": "application/vnd.oci.image.manifest.v1+json",
      "size": 7143,
      "digest": "sha256:e692418e4cbaf90ca69d05a66403747baa33ee08806650b51fab815ad7fc331f",
      "platform": {
        "architecture": "ppc64le",
        "os": "linux"
      }
    },
    {
      "mediaType": "application/vnd.oci.image.manifest.v1+json",
      "size": 7682,
      "digest": "sha256:5b0bcabd1ed22e9fb1310cf6c2dec7cdef19f0ad69efa1f392e94a4333501270",
      "platform": {
        "architecture": "amd64",
        "os": "linux"
      }
    }
  ],
  "annotations": {
    "com.example.key1": "value1",
    "com.example.key2": "value2"
  }
}
"""

import logging
import json

from cachetools.func import lru_cache
from jsonschema import validate as validate_schema, ValidationError

from digest import digest_tools
from image.shared import ManifestException
from image.shared.interfaces import ManifestListInterface
from image.shared.schemautil import LazyManifestLoader
from image.oci import OCI_IMAGE_INDEX_CONTENT_TYPE, OCI_IMAGE_MANIFEST_CONTENT_TYPE
from image.oci.descriptor import get_descriptor_schema
from image.oci.manifest import OCIManifest
from util.bytes import Bytes


logger = logging.getLogger(__name__)

# Keys.
INDEX_VERSION_KEY = "schemaVersion"
INDEX_MEDIATYPE_KEY = "mediaType"
INDEX_SIZE_KEY = "size"
INDEX_DIGEST_KEY = "digest"
INDEX_URLS_KEY = "urls"
INDEX_MANIFESTS_KEY = "manifests"
INDEX_PLATFORM_KEY = "platform"
INDEX_ARCHITECTURE_KEY = "architecture"
INDEX_OS_KEY = "os"
INDEX_OS_VERSION_KEY = "os.version"
INDEX_OS_FEATURES_KEY = "os.features"
INDEX_FEATURES_KEY = "features"
INDEX_VARIANT_KEY = "variant"
INDEX_ANNOTATIONS_KEY = "annotations"

ALLOWED_MEDIA_TYPES = [
    OCI_IMAGE_MANIFEST_CONTENT_TYPE,
    OCI_IMAGE_INDEX_CONTENT_TYPE,
]


class MalformedIndex(ManifestException):
    """
    Raised when a index fails an assertion that should be true according to the OCI Index spec.
    """

    pass


class OCIIndex(ManifestListInterface):
    METASCHEMA = {
        "type": "object",
        "properties": {
            INDEX_VERSION_KEY: {
                "type": "number",
                "description": "The version of the index. Must always be `2`.",
                "minimum": 2,
                "maximum": 2,
            },
            INDEX_MEDIATYPE_KEY: {
                "type": "string",
                "description": "The media type of the index.",
                "enum": [OCI_IMAGE_INDEX_CONTENT_TYPE],
            },
            INDEX_MANIFESTS_KEY: {
                "type": "array",
                "description": "The manifests field contains a list of manifests for specific platforms",
                "items": get_descriptor_schema(
                    allowed_media_types=ALLOWED_MEDIA_TYPES,
                    additional_properties={
                        INDEX_PLATFORM_KEY: {
                            "type": "object",
                            "description": "The platform object describes the platform which the image in "
                            + "the manifest runs on",
                            "properties": {
                                INDEX_ARCHITECTURE_KEY: {
                                    "type": "string",
                                    "description": "Specifies the CPU architecture, for example amd64 or ppc64le.",
                                },
                                INDEX_OS_KEY: {
                                    "type": "string",
                                    "description": "Specifies the operating system, for example linux or windows",
                                },
                                INDEX_OS_VERSION_KEY: {
                                    "type": "string",
                                    "description": "Specifies the operating system version, for example 10.0.10586",
                                },
                                INDEX_OS_FEATURES_KEY: {
                                    "type": "array",
                                    "description": "specifies an array of strings, each listing a required OS "
                                    + "feature (for example on Windows win32k)",
                                    "items": {"type": "string",},
                                },
                                INDEX_VARIANT_KEY: {
                                    "type": "string",
                                    "description": "Specifies a variant of the CPU, for example armv6l to specify "
                                    + "a particular CPU variant of the ARM CPU",
                                },
                                INDEX_FEATURES_KEY: {
                                    "type": "array",
                                    "description": "specifies an array of strings, each listing a required CPU "
                                    + "feature (for example sse4 or aes).",
                                    "items": {"type": "string",},
                                },
                            },
                            "required": [INDEX_ARCHITECTURE_KEY, INDEX_OS_KEY,],
                        },
                    },
                    additional_required=[INDEX_PLATFORM_KEY],
                ),
            },
            INDEX_ANNOTATIONS_KEY: {
                "type": "object",
                "description": "The annotations, if any, on this index",
                "additionalProperties": True,
            },
        },
        "required": [INDEX_VERSION_KEY, INDEX_MANIFESTS_KEY,],
    }

    def __init__(self, manifest_bytes):
        assert isinstance(manifest_bytes, Bytes)

        self._layers = None
        self._manifest_bytes = manifest_bytes

        try:
            self._parsed = json.loads(manifest_bytes.as_unicode())
        except ValueError as ve:
            raise MalformedIndex("malformed manifest data: %s" % ve)

        try:
            validate_schema(self._parsed, OCIIndex.METASCHEMA)
        except ValidationError as ve:
            raise MalformedIndex("manifest data does not match schema: %s" % ve)

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
        return OCI_IMAGE_INDEX_CONTENT_TYPE

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
        manifests = self._parsed[INDEX_MANIFESTS_KEY]
        supported_types = {}
        supported_types[OCI_IMAGE_MANIFEST_CONTENT_TYPE] = OCIManifest
        supported_types[OCI_IMAGE_INDEX_CONTENT_TYPE] = OCIIndex
        return [
            LazyManifestLoader(
                m,
                content_retriever,
                supported_types,
                INDEX_DIGEST_KEY,
                INDEX_SIZE_KEY,
                INDEX_MEDIATYPE_KEY,
            )
            for m in manifests
        ]

    def validate(self, content_retriever):
        """
        Performs validation of required assertions about the manifest.

        Raises a ManifestException on failure.
        """
        # Nothing to validate.

    def child_manifests(self, content_retriever):
        return self.manifests(content_retriever)

    def child_manifest_digests(self):
        return [m[INDEX_DIGEST_KEY] for m in self._parsed[INDEX_MANIFESTS_KEY]]

    def get_manifest_labels(self, content_retriever):
        return None

    def get_leaf_layer_v1_image_id(self, content_retriever):
        return None

    def get_legacy_image_ids(self, content_retriever):
        return None

    @property
    def has_legacy_image(self):
        return False

    @property
    def amd64_linux_manifest_digest(self):
        """ Returns the digest of the AMD64+Linux manifest in this list, if any, or None
            if none.
        """
        for manifest_ref in self._parsed[INDEX_MANIFESTS_KEY]:
            platform = manifest_ref[INDEX_PLATFORM_KEY]
            architecture = platform.get(INDEX_ARCHITECTURE_KEY, None)
            os = platform.get(INDEX_OS_KEY, None)
            if architecture == "amd64" and os == "linux":
                return manifest_ref[INDEX_DIGEST_KEY]

        return None

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
            platform = manifest_ref._manifest_data[INDEX_PLATFORM_KEY]
            architecture = platform[INDEX_ARCHITECTURE_KEY]
            os = platform[INDEX_OS_KEY]
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


class OCIIndexBuilder(object):
    """
    A convenient abstraction around creating new OCIIndex's.
    """

    def __init__(self):
        self.manifests = []

    def add_manifest(self, manifest, architecture, os):
        """
        Adds a manifest to the list.
        """
        assert manifest.media_type in ALLOWED_MEDIA_TYPES
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
                {INDEX_ARCHITECTURE_KEY: architecture, INDEX_OS_KEY: os,},
            )
        )

    def build(self):
        """
        Builds and returns the DockerSchema2ManifestList.
        """
        assert self.manifests

        manifest_list_dict = {
            INDEX_VERSION_KEY: 2,
            INDEX_MEDIATYPE_KEY: OCI_IMAGE_INDEX_CONTENT_TYPE,
            INDEX_MANIFESTS_KEY: [
                {
                    INDEX_MEDIATYPE_KEY: manifest[2],
                    INDEX_DIGEST_KEY: manifest[0],
                    INDEX_SIZE_KEY: manifest[1],
                    INDEX_PLATFORM_KEY: manifest[3],
                }
                for manifest in self.manifests
            ],
        }

        json_str = Bytes.for_string_or_unicode(json.dumps(manifest_list_dict, indent=3))
        return OCIIndex(json_str)
