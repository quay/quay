import hashlib

from collections import namedtuple
from enum import Enum, unique

from cachetools.func import lru_cache

from data import model
from data.database import Manifest as ManifestTable
from data.registry_model.datatype import datatype, requiresinput, optionalinput
from image.docker import ManifestException
from image.docker.schemas import parse_manifest_from_bytes
from image.docker.schema1 import DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE
from image.docker.schema2 import DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE
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
            media_type_name=label.media_type.name,
            source_type_name=label.source_type.name,
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

    @classmethod
    def for_repository_tag(cls, repository_tag):
        if repository_tag is None:
            return None

        return ShallowTag(db_id=repository_tag.id, name=repository_tag.name)

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
    def for_tag(cls, tag, legacy_image=None):
        if tag is None:
            return None

        return Tag(
            db_id=tag.id,
            name=tag.name,
            reversion=tag.reversion,
            lifetime_start_ms=tag.lifetime_start_ms,
            lifetime_end_ms=tag.lifetime_end_ms,
            lifetime_start_ts=tag.lifetime_start_ms / 1000,
            lifetime_end_ts=tag.lifetime_end_ms / 1000 if tag.lifetime_end_ms else None,
            manifest_digest=tag.manifest.digest,
            inputs=dict(
                legacy_image=legacy_image,
                manifest=tag.manifest,
                repository=RepositoryReference.for_id(tag.repository_id),
            ),
        )

    @classmethod
    def for_repository_tag(cls, repository_tag, manifest_digest=None, legacy_image=None):
        if repository_tag is None:
            return None

        return Tag(
            db_id=repository_tag.id,
            name=repository_tag.name,
            reversion=repository_tag.reversion,
            lifetime_start_ts=repository_tag.lifetime_start_ts,
            lifetime_end_ts=repository_tag.lifetime_end_ts,
            lifetime_start_ms=repository_tag.lifetime_start_ts * 1000,
            lifetime_end_ms=(
                repository_tag.lifetime_end_ts * 1000 if repository_tag.lifetime_end_ts else None
            ),
            manifest_digest=manifest_digest,
            inputs=dict(
                legacy_image=legacy_image,
                repository=RepositoryReference.for_id(repository_tag.repository_id),
            ),
        )

    @property
    @requiresinput("manifest")
    def _manifest(self, manifest):
        """
        Returns the manifest for this tag.

        Will only apply to new-style OCI tags.
        """
        return manifest

    @property
    @optionalinput("manifest")
    def manifest(self, manifest):
        """
        Returns the manifest for this tag or None if none.

        Will only apply to new-style OCI tags.
        """
        return Manifest.for_manifest(manifest, self.legacy_image_if_present)

    @property
    @requiresinput("repository")
    def repository(self, repository):
        """
        Returns the repository under which this tag lives.
        """
        return repository

    @property
    @requiresinput("legacy_image")
    def legacy_image(self, legacy_image):
        """
        Returns the legacy Docker V1-style image for this tag.

        Note that this will be None for tags whose manifests point to other manifests instead of
        images.
        """
        return legacy_image

    @property
    @optionalinput("legacy_image")
    def legacy_image_if_present(self, legacy_image):
        """
        Returns the legacy Docker V1-style image for this tag.

        Note that this will be None for tags whose manifests point to other manifests instead of
        images.
        """
        return legacy_image

    @property
    def id(self):
        """
        The ID of this tag for pagination purposes only.
        """
        return self._db_id


class Manifest(datatype("Manifest", ["digest", "media_type", "internal_manifest_bytes"])):
    """
    Manifest represents a manifest in a repository.
    """

    @classmethod
    def for_tag_manifest(cls, tag_manifest, legacy_image=None):
        if tag_manifest is None:
            return None

        return Manifest(
            db_id=tag_manifest.id,
            digest=tag_manifest.digest,
            internal_manifest_bytes=Bytes.for_string_or_unicode(tag_manifest.json_data),
            media_type=DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE,  # Always in legacy.
            inputs=dict(legacy_image=legacy_image, tag_manifest=True),
        )

    @classmethod
    def for_manifest(cls, manifest, legacy_image):
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
            inputs=dict(legacy_image=legacy_image, tag_manifest=False),
        )

    @property
    @requiresinput("tag_manifest")
    def _is_tag_manifest(self, tag_manifest):
        return tag_manifest

    @property
    @requiresinput("legacy_image")
    def legacy_image(self, legacy_image):
        """
        Returns the legacy Docker V1-style image for this manifest.
        """
        return legacy_image

    @property
    @optionalinput("legacy_image")
    def legacy_image_if_present(self, legacy_image):
        """
        Returns the legacy Docker V1-style image for this manifest.

        Note that this will be None for manifests that point to other manifests instead of images.
        """
        return legacy_image

    def get_parsed_manifest(self, validate=True):
        """
        Returns the parsed manifest for this manifest.
        """
        assert self.internal_manifest_bytes
        return parse_manifest_from_bytes(
            self.internal_manifest_bytes, self.media_type, validate=validate
        )

    @property
    def layers_compressed_size(self):
        """
        Returns the total compressed size of the layers in the manifest or None if this could not be
        computed.
        """
        try:
            return self.get_parsed_manifest().layers_compressed_size
        except ManifestException:
            return None

    @property
    def is_manifest_list(self):
        """
        Returns True if this manifest points to a list (instead of an image).
        """
        return self.media_type == DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE


class LegacyImage(
    datatype(
        "LegacyImage",
        [
            "docker_image_id",
            "created",
            "comment",
            "command",
            "image_size",
            "aggregate_size",
            "uploading",
            "v1_metadata_string",
        ],
    )
):
    """
    LegacyImage represents a Docker V1-style image found in a repository.
    """

    @classmethod
    def for_image(cls, image, images_map=None, tags_map=None, blob=None):
        if image is None:
            return None

        return LegacyImage(
            db_id=image.id,
            inputs=dict(
                images_map=images_map,
                tags_map=tags_map,
                ancestor_id_list=image.ancestor_id_list(),
                blob=blob,
            ),
            docker_image_id=image.docker_image_id,
            created=image.created,
            comment=image.comment,
            command=image.command,
            v1_metadata_string=image.v1_json_metadata,
            image_size=image.storage.image_size,
            aggregate_size=image.aggregate_size,
            uploading=image.storage.uploading,
        )

    @property
    def id(self):
        """
        Returns the database ID of the legacy image.
        """
        return self._db_id

    @property
    @requiresinput("images_map")
    @requiresinput("ancestor_id_list")
    def parents(self, images_map, ancestor_id_list):
        """
        Returns the parent images for this image.

        Raises an exception if the parents have not been loaded before this property is invoked.
        Parents are returned starting at the leaf image.
        """
        return [
            LegacyImage.for_image(images_map[ancestor_id], images_map=images_map)
            for ancestor_id in reversed(ancestor_id_list)
            if images_map.get(ancestor_id)
        ]

    @property
    @requiresinput("blob")
    def blob(self, blob):
        """
        Returns the blob for this image.

        Raises an exception if the blob has not been loaded before this property is invoked.
        """
        return blob

    @property
    @requiresinput("tags_map")
    def tags(self, tags_map):
        """
        Returns the tags pointing to this image.

        Raises an exception if the tags have not been loaded before this property is invoked.
        """
        tags = tags_map.get(self._db_id)
        if not tags:
            return []

        return [Tag.for_repository_tag(tag) for tag in tags]


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
        # TODO: change this to take in the storage engine?
        return storage_path

    @property
    @requiresinput("placements")
    def placements(self, placements):
        """
        Returns all the storage placements at which the Blob can be found.
        """
        return placements


class DerivedImage(datatype("DerivedImage", ["verb", "varying_metadata", "blob"])):
    """
    DerivedImage represents an image derived from a manifest via some form of verb.
    """

    @classmethod
    def for_derived_storage(cls, derived, verb, varying_metadata, blob):
        return DerivedImage(
            db_id=derived.id, verb=verb, varying_metadata=varying_metadata, blob=blob
        )

    @property
    def unique_id(self):
        """
        Returns a unique ID for this derived image.

        This call will consistently produce the same unique ID across calls in the same code base.
        """
        return hashlib.sha256(("%s:%s" % (self.verb, self._db_id)).encode("utf-8")).hexdigest()


class TorrentInfo(datatype("TorrentInfo", ["pieces", "piece_length"])):
    """
    TorrentInfo represents information to pull a blob via torrent.
    """

    @classmethod
    def for_torrent_info(cls, torrent_info):
        return TorrentInfo(
            db_id=torrent_info.id,
            pieces=torrent_info.pieces,
            piece_length=torrent_info.piece_length,
        )


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

    @classmethod
    def for_repository_tag(cls, tag, repository):
        tag_layer_id = "%s.%s" % (tag.image.docker_image_id, tag.image.storage.uuid)
        return LikelyVulnerableTag(
            db_id=tag.id, name=tag.name, layer_id=tag_layer_id, inputs=dict(repository=repository)
        )

    @property
    @requiresinput("repository")
    def repository(self, repository):
        return RepositoryReference.for_repo_obj(repository)
