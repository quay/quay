import hashlib
import json

from collections import namedtuple
from enum import Enum, unique

from cachetools.func import lru_cache

from data import model
from data.database import Manifest as ManifestTable
from data.registry_model.datatype import datatype, requiresinput, optionalinput
from image.shared import ManifestException
from image.shared.schemas import parse_manifest_from_bytes, is_manifest_list_type
from image.docker.schema1 import DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE
from util.bytes import Bytes


class RepositoryReference(datatype("Repository", [])):
    """
    RepositoryReference is a reference to a repository, passed to registry interface methods.
    """

    @classmethod
    def for_repo_obj(
        cls, repo_obj, namespace_name=None, repo_name=None, is_free_namespace=None, state=None
    ):
        if repo_obj is None:
            return None

        return RepositoryReference(
            db_id=repo_obj.id,
            inputs=dict(
                kind=model.repository.get_repo_kind_name(repo_obj),
                is_public=model.repository.is_repository_public(repo_obj),
                namespace_name=namespace_name,
                repo_name=repo_name,
                is_free_namespace=is_free_namespace,
                state=state,
            ),
        )

    @classmethod
    def for_id(
        cls, repo_id, namespace_name=None, repo_name=None, is_free_namespace=None, state=None
    ):
        return RepositoryReference(
            db_id=repo_id,
            inputs=dict(
                kind=None,
                is_public=None,
                namespace_name=namespace_name,
                repo_name=repo_name,
                is_free_namespace=is_free_namespace,
                state=state,
            ),
        )

    @property
    @lru_cache(maxsize=1)
    def _repository_obj(self):
        return model.repository.lookup_repository(self._db_id)

    @property
    @optionalinput("kind")
    def kind(self, kind):
        """
        Returns the kind of the repository.
        """
        return kind or model.repository.get_repo_kind_name(self._repositry_obj)

    @property
    @optionalinput("is_public")
    def is_public(self, is_public):
        """
        Returns whether the repository is public.
        """
        if is_public is not None:
            return is_public

        return model.repository.is_repository_public(self._repository_obj)

    @property
    def trust_enabled(self):
        """
        Returns whether trust is enabled in this repository.
        """
        repository = self._repository_obj
        if repository is None:
            return None

        return repository.trust_enabled

    @property
    def id(self):
        """
        Returns the database ID of the repository.
        """
        return self._db_id

    @property
    @optionalinput("namespace_name")
    def namespace_name(self, namespace_name=None):
        """
        Returns the namespace name of this repository.
        """
        if namespace_name is not None:
            return namespace_name

        repository = self._repository_obj
        if repository is None:
            return None

        return repository.namespace_user.username

    @property
    @optionalinput("is_free_namespace")
    def is_free_namespace(self, is_free_namespace=None):
        """
        Returns whether the namespace of the repository is on a free plan.
        """
        if is_free_namespace is not None:
            return is_free_namespace

        repository = self._repository_obj
        if repository is None:
            return None

        return repository.namespace_user.stripe_id is None

    @property
    @optionalinput("repo_name")
    def name(self, repo_name=None):
        """
        Returns the name of this repository.
        """
        if repo_name is not None:
            return repo_name

        repository = self._repository_obj
        if repository is None:
            return None

        return repository.name

    @property
    @optionalinput("state")
    def state(self, state=None):
        """
        Return the state of the Repository.
        """
        if state is not None:
            return state

        repository = self._repository_obj
        if repository is None:
            return None

        return repository.state


class Label(datatype("Label", ["key", "value", "uuid", "source_type_name", "media_type_name"])):
    """
    Label represents a label on a manifest.
    """

    @classmethod
    def for_label(cls, label):
        if label is None:
            return None

        return Label(
            db_id=label.id,
            key=label.key,
            value=label.value,
            uuid=label.uuid,
            media_type_name=model.label.get_media_types()[label.media_type_id],
            source_type_name=model.label.get_label_source_types()[label.source_type_id],
        )


class ShallowTag(datatype("ShallowTag", ["name"])):
    """
    ShallowTag represents a tag in a repository, but only contains basic information.
    """

    @classmethod
    def for_tag(cls, tag):
        if tag is None:
            return None

        return ShallowTag(db_id=tag.id, name=tag.name)

    @property
    def id(self):
        """
        The ID of this tag for pagination purposes only.
        """
        return self._db_id


class Tag(
    datatype(
        "Tag",
        [
            "name",
            "reversion",
            "manifest_digest",
            "lifetime_start_ts",
            "lifetime_end_ts",
            "lifetime_start_ms",
            "lifetime_end_ms",
        ],
    )
):
    """
    Tag represents a tag in a repository, which points to a manifest or image.
    """

    @classmethod
    def for_tag(cls, tag, legacy_id_handler, manifest_row=None, legacy_image_row=None):
        if tag is None:
            return None

        return Tag(
            db_id=tag.id,
            name=tag.name,
            reversion=tag.reversion,
            lifetime_start_ms=tag.lifetime_start_ms,
            lifetime_end_ms=tag.lifetime_end_ms,
            lifetime_start_ts=tag.lifetime_start_ms // 1000,
            lifetime_end_ts=tag.lifetime_end_ms // 1000 if tag.lifetime_end_ms else None,
            manifest_digest=manifest_row.digest if manifest_row else tag.manifest.digest,
            inputs=dict(
                legacy_id_handler=legacy_id_handler,
                legacy_image_row=legacy_image_row,
                manifest_row=manifest_row or tag.manifest,
                repository=RepositoryReference.for_id(tag.repository_id),
            ),
        )

    @property
    @requiresinput("manifest_row")
    def _manifest_row(self, manifest_row):
        """
        Returns the database Manifest object for this tag.
        """
        return manifest_row

    @property
    @requiresinput("manifest_row")
    @requiresinput("legacy_id_handler")
    @optionalinput("legacy_image_row")
    def manifest(self, manifest_row, legacy_id_handler, legacy_image_row):
        """
        Returns the manifest for this tag.
        """
        return Manifest.for_manifest(
            manifest_row, legacy_id_handler, legacy_image_row=legacy_image_row
        )

    @property
    @requiresinput("repository")
    def repository(self, repository):
        """
        Returns the repository under which this tag lives.
        """
        return repository

    @property
    def id(self):
        """
        The ID of this tag for pagination purposes only.
        """
        return self._db_id

    @property
    def manifest_layers_size(self):
        """ Returns the compressed size of the layers of the manifest for the Tag or
            None if none applicable or loaded.
        """
        return self.manifest.layers_compressed_size


class Manifest(
    datatype(
        "Manifest",
        [
            "digest",
            "media_type",
            "config_media_type",
            "_layers_compressed_size",
            "internal_manifest_bytes",
        ],
    )
):
    """
    Manifest represents a manifest in a repository.
    """

    @classmethod
    def for_manifest(cls, manifest, legacy_id_handler, legacy_image_row=None):
        if manifest is None:
            return None

        # NOTE: `manifest_bytes` will be None if not selected by certain join queries.
        manifest_bytes = (
            Bytes.for_string_or_unicode(manifest.manifest_bytes)
            if manifest.manifest_bytes is not None
            else None
        )
        return Manifest(
            db_id=manifest.id,
            digest=manifest.digest,
            internal_manifest_bytes=manifest_bytes,
            media_type=ManifestTable.media_type.get_name(manifest.media_type_id),
            _layers_compressed_size=manifest.layers_compressed_size,
            config_media_type=manifest.config_media_type,
            inputs=dict(
                legacy_id_handler=legacy_id_handler,
                legacy_image_row=legacy_image_row,
                repository=RepositoryReference.for_id(manifest.repository_id),
            ),
        )

    def get_parsed_manifest(self, validate=True):
        """
        Returns the parsed manifest for this manifest.
        """
        assert self.internal_manifest_bytes
        return parse_manifest_from_bytes(
            self.internal_manifest_bytes, self.media_type, validate=validate
        )

    @property
    def is_manifest_list(self):
        """
        Returns True if this manifest points to a list (instead of an image).
        """
        return is_manifest_list_type(self.media_type)

    @property
    @requiresinput("repository")
    def repository(self, repository):
        """
        Returns the repository under which this manifest lives.
        """
        return repository

    @property
    @optionalinput("legacy_image_row")
    def _legacy_image_row(self, legacy_image_row):
        return legacy_image_row

    @property
    def layers_compressed_size(self):
        # TODO: Simplify once we've stopped writing Image rows and we've backfilled the
        # sizes.

        # First check the manifest itself, as all newly written manifests will have the
        # size.
        if self._layers_compressed_size is not None:
            return self._layers_compressed_size

        # Secondly, check for the size of the legacy Image row.
        legacy_image_row = self._legacy_image_row
        if legacy_image_row:
            return legacy_image_row.aggregate_size

        # Otherwise, return None.
        return None

    @property
    @requiresinput("legacy_id_handler")
    def legacy_image_root_id(self, legacy_id_handler):
        """
        Returns the legacy Docker V1-style image ID for this manifest. Note that an ID will
        be returned even if the manifest does not support a legacy image.
        """
        return legacy_id_handler.encode(self._db_id)

    def as_manifest(self):
        """ Returns the manifest or legacy image as a manifest. """
        return self

    @property
    @requiresinput("legacy_id_handler")
    def _legacy_id_handler(self, legacy_id_handler):
        return legacy_id_handler

    def lookup_legacy_image(self, layer_index, retriever):
        """ Looks up and returns the legacy image for index-th layer in this manifest
            or None if none. The indexes here are from leaf to root, with index 0 being
            the leaf.
        """
        # Retrieve the schema1 manifest. If none exists, legacy images are not supported.
        parsed = self.get_parsed_manifest()
        if parsed is None:
            return None

        schema1 = parsed.get_schema1_manifest("$namespace", "$repo", "$tag", retriever)
        if schema1 is None:
            return None

        return LegacyImage.for_schema1_manifest_layer_index(
            self, schema1, layer_index, self._legacy_id_handler
        )


class LegacyImage(
    namedtuple(
        "LegacyImage",
        [
            "docker_image_id",
            "created",
            "comment",
            "command",
            "image_size",
            "aggregate_size",
            "blob",
            "blob_digest",
            "v1_metadata_string",
            # Internal fields.
            "layer_index",
            "manifest",
            "parsed_manifest",
            "id_handler",
        ],
    )
):
    """
    LegacyImage represents a Docker V1-style image found in a repository.
    """

    @classmethod
    def for_schema1_manifest_layer_index(
        cls, manifest, parsed_manifest, layer_index, id_handler, blob=None
    ):
        assert parsed_manifest.schema_version == 1
        layers = parsed_manifest.layers
        if layer_index >= len(layers):
            return None

        # NOTE: Schema1 keeps its layers in the order from base to leaf, so we have
        # to reverse our lookup order.
        leaf_to_base = list(reversed(layers))

        aggregated_size = sum(
            [
                l.compressed_size
                for index, l in enumerate(leaf_to_base)
                if index >= layer_index and l.compressed_size is not None
            ]
        )

        layer = leaf_to_base[layer_index]
        synthetic_layer_id = id_handler.encode(manifest._db_id, layer_index)

        # Replace the image ID and parent ID with our synethetic IDs.
        try:
            parsed = json.loads(layer.raw_v1_metadata)
            parsed["id"] = synthetic_layer_id
            if layer_index < len(leaf_to_base) - 1:
                parsed["parent"] = id_handler.encode(manifest._db_id, layer_index + 1)
        except (ValueError, TypeError):
            return None

        return LegacyImage(
            docker_image_id=synthetic_layer_id,
            created=layer.v1_metadata.created,
            comment=layer.v1_metadata.comment,
            command=layer.v1_metadata.command,
            image_size=layer.compressed_size,
            aggregate_size=aggregated_size,
            blob=blob,
            blob_digest=layer.digest,
            v1_metadata_string=json.dumps(parsed),
            layer_index=layer_index,
            manifest=manifest,
            parsed_manifest=parsed_manifest,
            id_handler=id_handler,
        )

    def with_blob(self, blob):
        """ Sets the blob for the legacy image. """
        return self._replace(blob=blob)

    @property
    def parent_image_id(self):
        ancestor_ids = self.ancestor_ids
        if not ancestor_ids:
            return None

        return ancestor_ids[-1]

    @property
    def ancestor_ids(self):
        ancestor_ids = []
        for layer_index in range(self.layer_index + 1, len(self.parsed_manifest.layers)):
            ancestor_ids.append(self.id_handler.encode(self.manifest._db_id, layer_index))
        return ancestor_ids

    @property
    def full_image_id_chain(self):
        return [self.docker_image_id] + self.ancestor_ids

    def as_manifest(self):
        """ Returns the parent manifest for the legacy image. """
        return self.manifest


@unique
class SecurityScanStatus(Enum):
    """
    Security scan status enum.
    """

    SCANNED = "scanned"
    FAILED = "failed"
    QUEUED = "queued"
    UNSUPPORTED = "unsupported"


class ManifestLayer(namedtuple("ManifestLayer", ["layer_info", "blob"])):
    """
    Represents a single layer in a manifest.

    The `layer_info` data will be manifest-type specific, but will have a few expected fields (such
    as `digest`). The `blob` represents the associated blob for this layer, optionally with
    placements. If the layer is a remote layer, the blob will be None.
    """

    def estimated_size(self, estimate_multiplier):
        """
        Returns the estimated size of this layer.

        If the layers' blob has an uncompressed size, it is used. Otherwise, the compressed_size
        field in the layer is multiplied by the multiplier.
        """
        if self.blob.uncompressed_size:
            return self.blob.uncompressed_size

        return (self.layer_info.compressed_size or 0) * estimate_multiplier


class Blob(
    datatype("Blob", ["uuid", "digest", "compressed_size", "uncompressed_size", "uploading"])
):
    """
    Blob represents a content-addressable piece of storage.
    """

    @classmethod
    def for_image_storage(cls, image_storage, storage_path, placements=None):
        if image_storage is None:
            return None

        return Blob(
            db_id=image_storage.id,
            uuid=image_storage.uuid,
            inputs=dict(placements=placements, storage_path=storage_path),
            digest=image_storage.content_checksum,
            compressed_size=image_storage.image_size,
            uncompressed_size=image_storage.uncompressed_size,
            uploading=image_storage.uploading,
        )

    @property
    @requiresinput("storage_path")
    def storage_path(self, storage_path):
        """
        Returns the path of this blob in storage.
        """
        return storage_path

    @property
    @requiresinput("placements")
    def placements(self, placements):
        """
        Returns all the storage placements at which the Blob can be found.
        """
        return placements


class BlobUpload(
    datatype(
        "BlobUpload",
        [
            "upload_id",
            "byte_count",
            "uncompressed_byte_count",
            "chunk_count",
            "sha_state",
            "location_name",
            "storage_metadata",
            "piece_sha_state",
            "piece_hashes",
        ],
    )
):
    """
    BlobUpload represents information about an in-progress upload to create a blob.
    """

    @classmethod
    def for_upload(cls, blob_upload, location_name=None):
        return BlobUpload(
            db_id=blob_upload.id,
            upload_id=blob_upload.uuid,
            byte_count=blob_upload.byte_count,
            uncompressed_byte_count=blob_upload.uncompressed_byte_count,
            chunk_count=blob_upload.chunk_count,
            sha_state=blob_upload.sha_state,
            location_name=location_name or blob_upload.location.name,
            storage_metadata=blob_upload.storage_metadata,
            piece_sha_state=blob_upload.piece_sha_state,
            piece_hashes=blob_upload.piece_hashes,
        )


class LikelyVulnerableTag(datatype("LikelyVulnerableTag", ["layer_id", "name"])):
    """
    LikelyVulnerableTag represents a tag in a repository that is likely vulnerable to a notified
    vulnerability.
    """

    # TODO: Remove all of this once we're on the new security model exclusively.
    @classmethod
    def for_tag(cls, tag, repository, docker_image_id, storage_uuid):
        layer_id = "%s.%s" % (docker_image_id, storage_uuid)
        return LikelyVulnerableTag(
            db_id=tag.id, name=tag.name, layer_id=layer_id, inputs=dict(repository=repository)
        )

    @property
    @requiresinput("repository")
    def repository(self, repository):
        return RepositoryReference.for_repo_obj(repository)
