"""
Implements validation and conversion for the OCI Manifest JSON.

See: https://github.com/opencontainers/image-spec/blob/master/manifest.md

Example:

{
  "mediaType": "application/vnd.oci.artifact.manifest.v1+json",
  "artifactType": "application/vnd.example.sbom.v1",
  "blobs": [
    {
      "mediaType": "application/gzip",
      "size": 123,
      "digest": "sha256:87923725d74f4bfb94c9e86d64170f7521aad8221a5de834851470ca142da630"
    }
  ],
  "subject": {
    "mediaType": "application/vnd.oci.image.manifest.v1+json",
    "size": 1234,
    "digest": "sha256:cc06a2839488b8bd2a2b99dcdc03d5cfd818eed72ad08ef3cc197aac64c0d0a0"
  },
  "annotations": {
    "org.opencontainers.artifact.created": "2022-01-01T14:42:55Z",
    "org.example.sbom.format": "json"
  }
}

"""

import json
import logging

from collections import namedtuple
from typing import Optional
from jsonschema import validate as validate_schema, ValidationError

from digest import digest_tools
from image.shared import ManifestException
from image.shared.interfaces import ManifestInterface
from image.oci import OCI_ARTIFACT_MANIFEST_CONTENT_TYPE
from image.oci.descriptor import get_descriptor_schema
from util.bytes import Bytes

# Keys.
OCI_ARTIFACT_MANIFEST_MEDIATYPE_KEY = "mediaType"
OCI_ARTIFACT_MANIFEST_ARTIFACTTYPE_KEY = "artifactType"
OCI_ARTIFACT_MANIFEST_SIZE_KEY = "size"
OCI_ARTIFACT_MANIFEST_URLS_KEY = "size"
OCI_ARTIFACT_MANIFEST_DIGEST_KEY = "digest"
OCI_ARTIFACT_MANIFEST_BLOBS_KEY = "blobs"
OCI_ARTIFACT_MANIFEST_ANNOTATIONS_KEY = "annotations"
OCI_ARTIFACT_MANIFEST_SUBJECT_KEY = "subject"


# Named tuples.
OCIArtifactBlob = namedtuple(
    "OCIArtifactBlob", ["index", "content_type", "digest", "urls", "compressed_size"]
)


logger = logging.getLogger(__name__)


class MalformedOCIArtifactManifest(ManifestException):
    """
    Raised when a manifest fails an assertion that should be true according to the OCI Manifest
    spec.
    """

    pass


# TODO: Not all fields in this class have been implemented thoroughly
class OCIArtifactManifest(ManifestInterface):
    def get_meta_schema(self):
        """
        Since the layers are dynamic based on config, populate them here before using
        """
        METASCHEMA = {
            "type": "object",
            "properties": {
                OCI_ARTIFACT_MANIFEST_MEDIATYPE_KEY: {
                    "type": "string",
                    "description": "The media type of the schema.",
                    "enum": [OCI_ARTIFACT_MANIFEST_CONTENT_TYPE],
                },
                OCI_ARTIFACT_MANIFEST_ARTIFACTTYPE_KEY: {
                    "type": "string",
                    "description": "",
                },
                OCI_ARTIFACT_MANIFEST_BLOBS_KEY: {
                    "type": "array",
                    "description": "The array MUST have the base layer at index 0. Subsequent layers MUST then follow in stack order (i.e. from layers[0] to layers[len(layers)-1])",
                    "items": get_descriptor_schema(),
                },
                OCI_ARTIFACT_MANIFEST_SUBJECT_KEY: {
                    "type": "object",
                    "description": "Used to inditify subject manifest",
                    "properties": {
                        OCI_ARTIFACT_MANIFEST_MEDIATYPE_KEY: {
                            "type": "string",
                            "description": "The MIME type of the referenced object. This should generally be "
                            + "application/vnd.docker.container.image.v1+json",
                        },
                        OCI_ARTIFACT_MANIFEST_SIZE_KEY: {
                            "type": "number",
                            "description": "The size in bytes of the object. This field exists so that a "
                            + "client will have an expected size for the content before "
                            + "validating. If the length of the retrieved content does not "
                            + "match the specified length, the content should not be trusted.",
                        },
                        OCI_ARTIFACT_MANIFEST_DIGEST_KEY: {
                            "type": "string",
                            "description": "The content addressable digest of the config in the blob store",
                        },
                    },
                },
                OCI_ARTIFACT_MANIFEST_ANNOTATIONS_KEY: {
                    "type": "object",
                    "description": "",
                },
            },
            "required": [
                OCI_ARTIFACT_MANIFEST_MEDIATYPE_KEY,
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
            raise MalformedOCIArtifactManifest("malformed manifest data: %s" % ve)

        try:
            validate_schema(self._parsed, self.get_meta_schema())
        except ValidationError as ve:
            raise MalformedOCIArtifactManifest("manifest data does not match schema: %s" % ve)

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
        return None

    @property
    def manifest_dict(self):
        return self._parsed

    @property
    def media_type(self):
        return OCI_ARTIFACT_MANIFEST_CONTENT_TYPE

    @property
    def artifact_type(self):
        return self._parsed.get(OCI_ARTIFACT_MANIFEST_ARTIFACTTYPE_KEY)

    @property
    def digest(self):
        return digest_tools.sha256_digest(self._payload.as_encoded_str())

    @property
    def config(self):
        return None

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
        return None

    @property
    def layers_compressed_size(self):
        return sum(layer.compressed_size for layer in self.filesystem_layers)

    @property
    def has_remote_layer(self):
        return None

    @property
    def is_image_manifest(self):
        return False

    @property
    def blob_digests(self):
        return [str(layer.digest) for layer in self.filesystem_layers]

    @property
    def local_blob_digests(self):
        return [str(layer.digest) for layer in self.filesystem_layers]

    @property
    def annotations(self):
        """Returns the annotations on the manifest itself."""
        return self._parsed.get(OCI_ARTIFACT_MANIFEST_ANNOTATIONS_KEY) or {}

    @property
    def subject(self) -> str:
        return self._parsed.get(OCI_ARTIFACT_MANIFEST_SUBJECT_KEY, {}).get(
            OCI_ARTIFACT_MANIFEST_DIGEST_KEY
        )

    def get_blob_digests_for_translation(self):
        return self.blob_digests

    def get_manifest_labels(self, content_retriever):
        if not self.is_image_manifest:
            return dict(self.annotations)

        labels = {}
        labels.update(self.annotations)
        return labels

    def get_layers(self, content_retriever):
        """
        Returns the layers of this manifest, from base to leaf or None if this kind of manifest does
        not support layers.
        """
        return None

    @property
    def bytes(self):
        return self._payload

    def child_manifests(self, content_retriever):
        return None

    def _manifest_image_layers(self, content_retriever):
        return None

    @property
    def is_empty_manifest(self):
        return len(self._parsed[OCI_ARTIFACT_MANIFEST_BLOBS_KEY]) == 0

    @property
    def has_legacy_image(self):
        return None

    def generate_legacy_layers(self, images_map, content_retriever):
        return None

    def get_leaf_layer_v1_image_id(self, content_retriever):
        return None

    def get_legacy_image_ids(self, content_retriever):
        return None

    def convert_manifest(
        self, allowed_mediatypes, namespace_name, repo_name, tag_name, content_retriever
    ):
        return None

    def get_schema1_manifest(self, namespace_name, repo_name, tag_name, content_retriever):
        return None

    def unsigned(self):
        return self

    def get_requires_empty_layer_blob(self, content_retriever):
        return None

    def _populate_schema1_builder(self, v1_builder, content_retriever):
        return None

    def _get_built_config(self, content_retriever):
        return None

    def _generate_filesystem_layers(self):
        for index, blob in enumerate(self._parsed[OCI_ARTIFACT_MANIFEST_BLOBS_KEY]):
            content_type = blob[OCI_ARTIFACT_MANIFEST_MEDIATYPE_KEY]

            try:
                digest = digest_tools.Digest.parse_digest(blob[OCI_ARTIFACT_MANIFEST_DIGEST_KEY])
            except digest_tools.InvalidDigestException:
                raise MalformedOCIArtifactManifest(
                    "could not parse manifest digest: %s" % blob[OCI_ARTIFACT_MANIFEST_DIGEST_KEY]
                )

            yield OCIArtifactBlob(
                index=index,
                content_type=content_type,
                compressed_size=blob[OCI_ARTIFACT_MANIFEST_SIZE_KEY],
                digest=digest,
                urls=blob.get(OCI_ARTIFACT_MANIFEST_URLS_KEY),
            )


class OCIArtifactManifestBuilder(object):
    """
    A convenient abstraction around creating new OCIArtifactManifest.
    """

    def __init__(self, artifact_type: str):
        self.blobs: list[OCIArtifactBlob] = []
        self.artifact_type = artifact_type
        self.subject: Optional[OCIArtifactBlob] = None

    def clone(self):
        cloned = OCIArtifactManifestBuilder(self.artifact_type)
        cloned.blobs = list(self.blobs)
        cloned.subject = self.subject
        return cloned

    def add_layer(self, content_type, digest, size, urls=None):
        """
        Adds a blob to the manifest.
        """
        self.blobs.append(
            OCIArtifactBlob(
                index=len(self.blobs),
                content_type=content_type,
                digest=digest,
                compressed_size=size,
                urls=urls,
            )
        )

    def add_subject(self, subject: OCIArtifactBlob):
        self.subject = subject

    def build(self, ensure_ascii=True):
        """
        Builds and returns the OCIManifest.
        """
        assert self.blobs

        def _build_descriptor(layer):
            descriptor = {
                OCI_ARTIFACT_MANIFEST_MEDIATYPE_KEY: layer.content_type,
                OCI_ARTIFACT_MANIFEST_SIZE_KEY: layer.compressed_size,
                OCI_ARTIFACT_MANIFEST_DIGEST_KEY: str(layer.digest),
            }
            if layer.urls:
                descriptor[OCI_ARTIFACT_MANIFEST_URLS_KEY] = layer.urls
            return descriptor

        manifest_dict = {
            OCI_ARTIFACT_MANIFEST_MEDIATYPE_KEY: OCI_ARTIFACT_MANIFEST_CONTENT_TYPE,
            OCI_ARTIFACT_MANIFEST_ARTIFACTTYPE_KEY: self.artifact_type,
            OCI_ARTIFACT_MANIFEST_BLOBS_KEY: [_build_descriptor(layer) for layer in self.blobs],
        }

        if self.subject is not None:
            manifest_dict[OCI_ARTIFACT_MANIFEST_SUBJECT_KEY] = _build_descriptor(self.subject)

        json_str = json.dumps(manifest_dict, ensure_ascii=ensure_ascii, indent=3)
        return OCIArtifactManifest(Bytes.for_string_or_unicode(json_str))
