"""
schema1 implements pure data transformations according to the Docker Manifest v2.1 Specification.

https://github.com/docker/distribution/blob/master/docs/spec/manifest-v2-1.md
"""

import hashlib
import json
import logging

from collections import namedtuple, OrderedDict
from datetime import datetime

import dateutil.parser

from jsonschema import validate as validate_schema, ValidationError

from jwt.utils import base64url_encode, base64url_decode

from authlib.jose import JsonWebKey, JsonWebSignature
from authlib.jose.errors import BadSignatureError, UnsupportedAlgorithmError

from digest import digest_tools
from image.shared import ManifestException
from image.shared.types import ManifestImageLayer
from image.shared.interfaces import ManifestInterface
from image.shared.schemautil import to_canonical_json
from image.docker.v1 import DockerV1Metadata
from util.bytes import Bytes

logger = logging.getLogger(__name__)


# Content Types
DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE = "application/vnd.docker.distribution.manifest.v1+json"
DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE = (
    "application/vnd.docker.distribution.manifest.v1+prettyjws"
)
DOCKER_SCHEMA1_CONTENT_TYPES = {
    DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE,
}

# Keys for signature-related data
DOCKER_SCHEMA1_SIGNATURES_KEY = "signatures"
DOCKER_SCHEMA1_HEADER_KEY = "header"
DOCKER_SCHEMA1_SIGNATURE_KEY = "signature"
DOCKER_SCHEMA1_PROTECTED_KEY = "protected"
DOCKER_SCHEMA1_FORMAT_LENGTH_KEY = "formatLength"
DOCKER_SCHEMA1_FORMAT_TAIL_KEY = "formatTail"

# Keys for manifest-related data
DOCKER_SCHEMA1_REPO_NAME_KEY = "name"
DOCKER_SCHEMA1_REPO_TAG_KEY = "tag"
DOCKER_SCHEMA1_ARCH_KEY = "architecture"
DOCKER_SCHEMA1_FS_LAYERS_KEY = "fsLayers"
DOCKER_SCHEMA1_BLOB_SUM_KEY = "blobSum"
DOCKER_SCHEMA1_HISTORY_KEY = "history"
DOCKER_SCHEMA1_V1_COMPAT_KEY = "v1Compatibility"
DOCKER_SCHEMA1_SCHEMA_VER_KEY = "schemaVersion"

# Format for time used in the protected payload.
_ISO_DATETIME_FORMAT_ZULU = "%Y-%m-%dT%H:%M:%SZ"

# The algorithm we use to sign the JWS.
_JWS_SIGNING_ALGORITHM = "RS256"


class MalformedSchema1Manifest(ManifestException):
    """
    Raised when a manifest fails an assertion that should be true according to the Docker Manifest
    v2.1 Specification.
    """

    pass


class InvalidSchema1Signature(ManifestException):
    """
    Raised when there is a failure verifying the signature of a signed Docker 2.1 Manifest.
    """

    pass


class Schema1Layer(
    namedtuple(
        "Schema1Layer",
        ["digest", "v1_metadata", "raw_v1_metadata", "compressed_size", "is_remote", "urls"],
    )
):
    """
    Represents all of the data about an individual layer in a given Manifest.

    This is the union of the fsLayers (digest) and the history entries (v1_compatibility).
    """


class Schema1V1Metadata(
    namedtuple(
        "Schema1V1Metadata",
        ["image_id", "parent_image_id", "created", "comment", "command", "author", "labels"],
    )
):
    """
    Represents the necessary data extracted from the v1 compatibility string in a given layer of a
    Manifest.
    """


class DockerSchema1Manifest(ManifestInterface):
    METASCHEMA = {
        "type": "object",
        "properties": {
            DOCKER_SCHEMA1_SIGNATURES_KEY: {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        DOCKER_SCHEMA1_PROTECTED_KEY: {
                            "type": "string",
                        },
                        DOCKER_SCHEMA1_HEADER_KEY: {
                            "type": "object",
                            "properties": {
                                "alg": {
                                    "type": "string",
                                },
                                "jwk": {
                                    "type": "object",
                                },
                            },
                            "required": ["alg", "jwk"],
                        },
                        DOCKER_SCHEMA1_SIGNATURE_KEY: {
                            "type": "string",
                        },
                    },
                    "required": [
                        DOCKER_SCHEMA1_PROTECTED_KEY,
                        DOCKER_SCHEMA1_HEADER_KEY,
                        DOCKER_SCHEMA1_SIGNATURE_KEY,
                    ],
                },
            },
            DOCKER_SCHEMA1_REPO_TAG_KEY: {
                "type": "string",
            },
            DOCKER_SCHEMA1_REPO_NAME_KEY: {
                "type": "string",
            },
            DOCKER_SCHEMA1_HISTORY_KEY: {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        DOCKER_SCHEMA1_V1_COMPAT_KEY: {
                            "type": "string",
                        },
                    },
                    "required": [DOCKER_SCHEMA1_V1_COMPAT_KEY],
                },
            },
            DOCKER_SCHEMA1_FS_LAYERS_KEY: {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        DOCKER_SCHEMA1_BLOB_SUM_KEY: {
                            "type": "string",
                        },
                    },
                    "required": [DOCKER_SCHEMA1_BLOB_SUM_KEY],
                },
            },
        },
        "required": [
            DOCKER_SCHEMA1_REPO_TAG_KEY,
            DOCKER_SCHEMA1_REPO_NAME_KEY,
            DOCKER_SCHEMA1_FS_LAYERS_KEY,
            DOCKER_SCHEMA1_HISTORY_KEY,
        ],
    }

    def __init__(self, manifest_bytes, validate=True):
        assert isinstance(manifest_bytes, Bytes)

        self._layers = None
        self._bytes = manifest_bytes

        try:
            self._parsed = json.loads(manifest_bytes.as_encoded_str())
        except ValueError as ve:
            raise MalformedSchema1Manifest("malformed manifest data: %s" % ve)

        try:
            validate_schema(self._parsed, DockerSchema1Manifest.METASCHEMA)
        except ValidationError as ve:
            raise MalformedSchema1Manifest("manifest data does not match schema: %s" % ve)

        self._signatures = self._parsed.get(DOCKER_SCHEMA1_SIGNATURES_KEY)
        self._architecture = self._parsed.get(DOCKER_SCHEMA1_ARCH_KEY)

        self._tag = self._parsed[DOCKER_SCHEMA1_REPO_TAG_KEY]

        repo_name = self._parsed[DOCKER_SCHEMA1_REPO_NAME_KEY]
        repo_name_tuple = repo_name.split("/", 1)
        if len(repo_name_tuple) > 1:
            self._namespace, self._repo_name = repo_name_tuple
        elif len(repo_name_tuple) == 1:
            self._namespace = ""
            self._repo_name = repo_name_tuple[0]
        else:
            raise MalformedSchema1Manifest("malformed repository name: %s" % repo_name)

        if validate:
            self._validate()

    def _validate(self):
        """
        Reference: https://docs.docker.com/registry/spec/manifest-v2-1/#signed-manifests
        """
        if not self._signatures:
            return

        payload_str = self._payload
        for signature in self._signatures:
            protected = signature[DOCKER_SCHEMA1_PROTECTED_KEY]
            sig = signature[DOCKER_SCHEMA1_SIGNATURE_KEY]

            jwk = JsonWebKey.import_key(signature[DOCKER_SCHEMA1_HEADER_KEY]["jwk"])
            jws = JsonWebSignature(algorithms=[signature[DOCKER_SCHEMA1_HEADER_KEY]["alg"]])

            obj_to_verify = {
                DOCKER_SCHEMA1_PROTECTED_KEY: protected,
                DOCKER_SCHEMA1_SIGNATURE_KEY: sig,
                DOCKER_SCHEMA1_HEADER_KEY: {"alg": signature[DOCKER_SCHEMA1_HEADER_KEY]["alg"]},
                "payload": base64url_encode(payload_str),
            }

            try:
                data = jws.deserialize_json(obj_to_verify, jwk.get_public_key())
            except (BadSignatureError, UnsupportedAlgorithmError):
                raise InvalidSchema1Signature()

            if not data:
                raise InvalidSchema1Signature()

    def validate(self, content_retriever):
        """
        Performs validation of required assertions about the manifest.

        Raises a ManifestException on failure.
        """
        # Validate the parent image IDs.
        encountered_ids = set()
        for layer in self.layers:
            if layer.v1_metadata.parent_image_id:
                if layer.v1_metadata.parent_image_id not in encountered_ids:
                    raise ManifestException(
                        "Unknown parent image %s" % layer.v1_metadata.parent_image_id
                    )

            if layer.v1_metadata.image_id:
                encountered_ids.add(layer.v1_metadata.image_id)

    @property
    def is_signed(self):
        """
        Returns whether the schema is signed.
        """
        return bool(self._signatures)

    @property
    def architecture(self):
        return self._architecture

    @property
    def is_manifest_list(self):
        return False

    @property
    def schema_version(self):
        return 1

    @property
    def content_type(self):
        return (
            DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE
            if self._signatures
            else DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE
        )

    @property
    def media_type(self):
        return self.content_type

    @property
    def signatures(self):
        return self._signatures

    @property
    def namespace(self):
        return self._namespace

    @property
    def repo_name(self):
        return self._repo_name

    @property
    def tag(self):
        return self._tag

    @property
    def bytes(self):
        return self._bytes

    @property
    def manifest_json(self):
        return self._parsed

    @property
    def manifest_dict(self):
        return self._parsed

    @property
    def layers_compressed_size(self):
        return sum(l.compressed_size for l in self.layers if l.compressed_size is not None)

    @property
    def config_media_type(self):
        return None

    @property
    def digest(self):
        return digest_tools.sha256_digest(self._payload)

    @property
    def image_ids(self):
        return {mdata.v1_metadata.image_id for mdata in self.layers}

    @property
    def parent_image_ids(self):
        return {
            mdata.v1_metadata.parent_image_id
            for mdata in self.layers
            if mdata.v1_metadata.parent_image_id
        }

    @property
    def checksums(self):
        return list({str(mdata.digest) for mdata in self.layers})

    @property
    def leaf_layer(self):
        return self.layers[-1]

    @property
    def created_datetime(self):
        created_datetime_str = self.leaf_layer.v1_metadata.created
        if created_datetime_str is None:
            return None

        try:
            return dateutil.parser.parse(created_datetime_str).replace(tzinfo=None)
        except:
            # parse raises different exceptions, so we cannot use a specific kind of handler here.
            return None

    @property
    def layers(self):
        if self._layers is None:
            self._layers = list(self._generate_layers())
        return self._layers

    def get_layers(self, content_retriever):
        """
        Returns the layers of this manifest, from base to leaf or None if this kind of manifest does
        not support layers.
        """
        for layer in self.layers:
            created_datetime = None
            try:
                created_datetime = dateutil.parser.parse(layer.v1_metadata.created).replace(
                    tzinfo=None
                )
            except:
                pass

            yield ManifestImageLayer(
                layer_id=layer.v1_metadata.image_id,
                compressed_size=layer.compressed_size,
                is_remote=False,
                urls=None,
                command=layer.v1_metadata.command,
                comment=layer.v1_metadata.comment,
                author=layer.v1_metadata.author,
                blob_digest=layer.digest,
                created_datetime=created_datetime,
                internal_layer=layer,
            )

    @property
    def blob_digests(self):
        return [str(layer.digest) for layer in self.layers]

    @property
    def local_blob_digests(self):
        return self.blob_digests

    def get_blob_digests_for_translation(self):
        """
        Returns the blob digests for translation of this manifest into another manifest.

        This method will ignore missing IDs in layers, unlike `blob_digests`.
        """
        layers = self._generate_layers(allow_missing_ids=True)
        return [str(layer.digest) for layer in layers]

    def child_manifests(self, content_retriever):
        return None

    def get_manifest_labels(self, content_retriever):
        return self.layers[-1].v1_metadata.labels

    def get_requires_empty_layer_blob(self, content_retriever):
        return False

    def _unsigned_builder(self):
        builder = DockerSchema1ManifestBuilder(
            self._namespace, self._repo_name, self._tag, self._architecture
        )
        for layer in reversed(self.layers):
            builder.add_layer(str(layer.digest), layer.raw_v1_metadata)

        return builder

    def unsigned(self):
        if self.media_type == DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE:
            return self

        # Create an unsigned version of the manifest.
        return self._unsigned_builder().build()

    def with_tag_name(self, tag_name, json_web_key=None):
        """
        Returns a copy of this manifest, with the tag changed to the given tag name.
        """
        builder = DockerSchema1ManifestBuilder(
            self._namespace, self._repo_name, tag_name, self._architecture
        )
        for layer in reversed(self.layers):
            builder.add_layer(str(layer.digest), layer.raw_v1_metadata)

        return builder.build(json_web_key)

    def _generate_layers(self, allow_missing_ids=False):
        """
        Returns a generator of objects that have the blobSum and v1Compatibility keys in them,
        starting from the base image and working toward the leaf node.
        """
        for blob_sum_obj, history_obj in reversed(
            list(
                zip(
                    self._parsed[DOCKER_SCHEMA1_FS_LAYERS_KEY],
                    self._parsed[DOCKER_SCHEMA1_HISTORY_KEY],
                )
            )
        ):

            try:
                image_digest = digest_tools.Digest.parse_digest(
                    blob_sum_obj[DOCKER_SCHEMA1_BLOB_SUM_KEY]
                )
            except digest_tools.InvalidDigestException:
                raise MalformedSchema1Manifest(
                    "could not parse manifest digest: %s"
                    % blob_sum_obj[DOCKER_SCHEMA1_BLOB_SUM_KEY]
                )

            metadata_string = history_obj[DOCKER_SCHEMA1_V1_COMPAT_KEY]

            try:
                v1_metadata = json.loads(metadata_string)
            except (ValueError, TypeError):
                raise MalformedSchema1Manifest(
                    "Could not parse metadata string: %s" % metadata_string
                )

            v1_metadata = v1_metadata or {}
            container_config = v1_metadata.get("container_config") or {}
            command_list = container_config.get("Cmd", None)
            command = to_canonical_json(command_list) if command_list else None

            if not allow_missing_ids and not "id" in v1_metadata:
                raise MalformedSchema1Manifest("id field missing from v1Compatibility JSON")

            labels = v1_metadata.get("config", {}).get("Labels", {}) or {}
            extracted = Schema1V1Metadata(
                image_id=v1_metadata.get("id"),
                parent_image_id=v1_metadata.get("parent"),
                created=v1_metadata.get("created"),
                comment=v1_metadata.get("comment"),
                author=v1_metadata.get("author"),
                command=command,
                labels=labels,
            )

            compressed_size = v1_metadata.get("Size")
            yield Schema1Layer(
                image_digest, extracted, metadata_string, compressed_size, False, None
            )

    @property
    def _payload(self):
        if self._signatures is None:
            return self._bytes.as_encoded_str()

        byte_data = self._bytes.as_encoded_str()
        protected = str(self._signatures[0][DOCKER_SCHEMA1_PROTECTED_KEY])
        parsed_protected = json.loads(base64url_decode(protected))
        signed_content_head = byte_data[: parsed_protected[DOCKER_SCHEMA1_FORMAT_LENGTH_KEY]]
        signed_content_tail = base64url_decode(
            str(parsed_protected[DOCKER_SCHEMA1_FORMAT_TAIL_KEY])
        )
        return signed_content_head + signed_content_tail

    def generate_legacy_layers(self, images_map, content_retriever):
        return self.rewrite_invalid_image_ids(images_map)

    def get_legacy_image_ids(self, content_retriever):
        return self.legacy_image_ids

    @property
    def legacy_image_ids(self):
        return {mdata.v1_metadata.image_id for mdata in self.layers}

    @property
    def has_legacy_image(self):
        return True

    @property
    def leaf_layer_v1_image_id(self):
        return self.layers[-1].v1_metadata.image_id

    def get_leaf_layer_v1_image_id(self, content_retriever):
        return self.layers[-1].v1_metadata.image_id

    def get_schema1_manifest(self, namespace_name, repo_name, tag_name, content_retriever):
        """
        Returns the manifest that is compatible with V1, by virtue of being `amd64` and `linux`.

        If none, returns None.
        """
        # Note: schema1 *technically* supports non-amd64 architectures, but in practice these were never
        # used, so to ensure full backwards compatibility, we just always return the schema.
        return self

    def convert_manifest(
        self, allowed_mediatypes, namespace_name, repo_name, tag_name, content_retriever
    ):
        if self.media_type in allowed_mediatypes:
            return self

        unsigned = self.unsigned()
        if unsigned.media_type in allowed_mediatypes:
            return unsigned

        return None

    def rewrite_invalid_image_ids(self, images_map):
        """
        Rewrites Docker v1 image IDs and returns a generator of DockerV1Metadata.

        If Docker gives us a layer with a v1 image ID that already points to existing content, but
        the checksums don't match, then we need to rewrite the image ID to something new in order to
        ensure consistency.
        """

        # Used to synthesize a new "content addressable" image id
        digest_history = hashlib.sha256()
        has_rewritten_ids = False
        updated_id_map = {}

        for layer in self.layers:
            digest_str = str(layer.digest)
            extracted_v1_metadata = layer.v1_metadata
            working_image_id = extracted_v1_metadata.image_id

            # Update our digest_history hash for the new layer data.
            digest_history.update(digest_str.encode("utf-8"))
            digest_history.update("@".encode("utf-8"))
            digest_history.update(layer.raw_v1_metadata.encode("utf-8"))
            digest_history.update("|".encode("utf-8"))

            # Ensure that the v1 image's storage matches the V2 blob. If not, we've
            # found a data inconsistency and need to create a new layer ID for the V1
            # image, and all images that follow it in the ancestry chain.
            digest_mismatch = (
                extracted_v1_metadata.image_id in images_map
                and images_map[extracted_v1_metadata.image_id].content_checksum != digest_str
            )
            if digest_mismatch or has_rewritten_ids:
                working_image_id = digest_history.hexdigest()
                has_rewritten_ids = True

            # Store the new docker id in the map
            updated_id_map[extracted_v1_metadata.image_id] = working_image_id

            # Lookup the parent image for the layer, if any.
            parent_image_id = extracted_v1_metadata.parent_image_id
            if parent_image_id is not None:
                parent_image_id = updated_id_map.get(parent_image_id, parent_image_id)

            # Synthesize and store the v1 metadata in the db.
            v1_metadata_json = layer.raw_v1_metadata
            if has_rewritten_ids:
                v1_metadata_json = _updated_v1_metadata(v1_metadata_json, updated_id_map)

            updated_image = DockerV1Metadata(
                namespace_name=self.namespace,
                repo_name=self.repo_name,
                image_id=working_image_id,
                created=extracted_v1_metadata.created,
                comment=extracted_v1_metadata.comment,
                author=extracted_v1_metadata.author,
                command=extracted_v1_metadata.command,
                compat_json=v1_metadata_json,
                parent_image_id=parent_image_id,
                checksum=None,  # TODO: Check if we need this.
                content_checksum=digest_str,
            )

            yield updated_image


class DockerSchema1ManifestBuilder(object):
    """
    A convenient abstraction around creating new DockerSchema1Manifests.
    """

    def __init__(self, namespace_name, repo_name, tag, architecture="amd64"):
        repo_name_key = "{0}/{1}".format(namespace_name, repo_name)
        if namespace_name == "":
            repo_name_key = repo_name

        self._base_payload = {
            DOCKER_SCHEMA1_REPO_TAG_KEY: tag,
            DOCKER_SCHEMA1_REPO_NAME_KEY: repo_name_key,
            DOCKER_SCHEMA1_ARCH_KEY: architecture,
            DOCKER_SCHEMA1_SCHEMA_VER_KEY: 1,
        }

        self._fs_layer_digests = []
        self._history = []
        self._namespace_name = namespace_name
        self._repo_name = repo_name
        self._tag = tag
        self._architecture = architecture

    def clone(self, tag_name=None):
        builder = DockerSchema1ManifestBuilder(
            self._namespace_name, self._repo_name, tag_name or self._tag, self._architecture
        )
        builder._fs_layer_digests = list(self._fs_layer_digests)
        builder._history = list(self._history)
        return builder

    def add_layer(self, layer_digest, v1_json_metadata):
        self._fs_layer_digests.append(
            {
                DOCKER_SCHEMA1_BLOB_SUM_KEY: layer_digest,
            }
        )
        self._history.append(
            {
                DOCKER_SCHEMA1_V1_COMPAT_KEY: v1_json_metadata or "{}",
            }
        )
        return self

    def insert_layer(self, layer_digest, v1_json_metadata):
        self._fs_layer_digests.insert(
            0,
            {
                DOCKER_SCHEMA1_BLOB_SUM_KEY: layer_digest,
            },
        )
        self._history.insert(
            0,
            {
                DOCKER_SCHEMA1_V1_COMPAT_KEY: v1_json_metadata or "{}",
            },
        )
        return self

    def with_metadata_removed(self):
        """
        Returns a copy of the builder where every layer but the leaf layer has its metadata stripped
        down to the bare essentials.
        """
        builder = DockerSchema1ManifestBuilder(
            self._namespace_name, self._repo_name, self._tag, self._architecture
        )

        for index, fs_layer in enumerate(self._fs_layer_digests):
            try:
                metadata = json.loads(self._history[index][DOCKER_SCHEMA1_V1_COMPAT_KEY])
            except (ValueError, TypeError):
                logger.exception("Could not parse existing builder")
                raise MalformedSchema1Manifest

            fixed_metadata = {}
            if index == 0:  # Leaf layer is at index 0 in schema 1.
                fixed_metadata = metadata
            else:
                # Remove all container config from the metadata.
                fixed_metadata["id"] = metadata["id"]
                if "parent" in metadata:
                    fixed_metadata["parent"] = metadata["parent"]

                if "created" in metadata:
                    fixed_metadata["created"] = metadata["created"]

                if "author" in metadata:
                    fixed_metadata["author"] = metadata["author"]

                if "comment" in metadata:
                    fixed_metadata["comment"] = metadata["comment"]

                if "Size" in metadata:
                    fixed_metadata["Size"] = metadata["Size"]

                if "Cmd" in metadata.get("container_config", {}):
                    fixed_metadata["container_config"] = {
                        "Cmd": metadata["container_config"]["Cmd"],
                    }

            builder.add_layer(fs_layer[DOCKER_SCHEMA1_BLOB_SUM_KEY], json.dumps(fixed_metadata))

        return builder

    def build(self, json_web_key=None, ensure_ascii=True):
        """
        Builds a DockerSchema1Manifest object, with optional signature.

        NOTE: For backward compatibility, "JWS JSON Serialization" is used instead of "JWS Compact Serialization", since the latter **requires** that the
        "alg" headers be carried in the **protected** headers, which was never done before migrating to authlib (One shouldn't be using schema1 anyways)

        References:
            - https://tools.ietf.org/html/rfc7515#section-10.7
            - https://docs.docker.com/registry/spec/manifest-v2-1/#signed-manifests
        """
        payload = OrderedDict(self._base_payload)
        payload.update(
            {
                DOCKER_SCHEMA1_HISTORY_KEY: self._history,
                DOCKER_SCHEMA1_FS_LAYERS_KEY: self._fs_layer_digests,
            }
        )

        payload_str = json.dumps(payload, indent=3, ensure_ascii=ensure_ascii)
        if json_web_key is None:
            return DockerSchema1Manifest(Bytes.for_string_or_unicode(payload_str))

        payload_str = Bytes.for_string_or_unicode(payload_str).as_encoded_str()
        split_point = payload_str.rfind(b"\n}")

        protected_payload = {
            DOCKER_SCHEMA1_FORMAT_TAIL_KEY: base64url_encode(payload_str[split_point:]).decode(
                "ascii"
            ),
            DOCKER_SCHEMA1_FORMAT_LENGTH_KEY: split_point,
            "time": datetime.utcnow().strftime(_ISO_DATETIME_FORMAT_ZULU),
        }

        # Flattened JSON serialization header
        jws = JsonWebSignature(algorithms=[_JWS_SIGNING_ALGORITHM])
        headers = {
            "protected": protected_payload,
            "header": {"alg": _JWS_SIGNING_ALGORITHM},
        }

        signed = jws.serialize_json(headers, payload_str, json_web_key.get_private_key())
        protected = signed["protected"]
        signature = signed["signature"]
        logger.debug("Generated signature: %s", signature)
        logger.debug("Generated protected block: %s", protected)

        public_members = set(json_web_key.REQUIRED_JSON_FIELDS + json_web_key.ALLOWED_PARAMS)
        public_key = {
            comp: value
            for comp, value in list(json_web_key.as_dict().items())
            if comp in public_members
        }
        public_key["kty"] = json_web_key.kty

        signature_block = {
            DOCKER_SCHEMA1_HEADER_KEY: {"jwk": public_key, "alg": _JWS_SIGNING_ALGORITHM},
            DOCKER_SCHEMA1_SIGNATURE_KEY: signature,
            DOCKER_SCHEMA1_PROTECTED_KEY: protected,
        }

        logger.debug("Encoded signature block: %s", json.dumps(signature_block))
        payload.update({DOCKER_SCHEMA1_SIGNATURES_KEY: [signature_block]})

        json_str = json.dumps(payload, indent=3, ensure_ascii=ensure_ascii)
        return DockerSchema1Manifest(Bytes.for_string_or_unicode(json_str))


def _updated_v1_metadata(v1_metadata_json, updated_id_map):
    """
    Updates v1_metadata with new image IDs.
    """
    parsed = json.loads(v1_metadata_json)
    parsed["id"] = updated_id_map[parsed["id"]]

    if parsed.get("parent") and parsed["parent"] in updated_id_map:
        parsed["parent"] = updated_id_map[parsed["parent"]]

    if parsed.get("container_config", {}).get("Image"):
        existing_image = parsed["container_config"]["Image"]
        if existing_image in updated_id_map:
            parsed["container_config"]["image"] = updated_id_map[existing_image]

    return to_canonical_json(parsed)
