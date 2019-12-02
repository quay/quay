# pylint: disable=protected-access
import logging

from abc import abstractmethod
from collections import defaultdict

from data import database
from data import model
from data.cache import cache_key
from data.model.oci.retriever import RepositoryContentRetriever
from data.model.blob import get_shared_blob
from data.registry_model.datatype import FromDictionaryException
from data.registry_model.datatypes import (
    RepositoryReference,
    Blob,
    TorrentInfo,
    BlobUpload,
    LegacyImage,
    ManifestLayer,
    DerivedImage,
    ShallowTag,
)
from image.docker.schema1 import ManifestException, DockerSchema1ManifestBuilder
from image.docker.schema2 import EMPTY_LAYER_BLOB_DIGEST

logger = logging.getLogger(__name__)

# The maximum size for generated manifest after which we remove extra metadata.
MAXIMUM_GENERATED_MANIFEST_SIZE = 3 * 1024 * 1024  # 3 MB


class SharedModel:
    """
  SharedModel implements those data model operations for the registry API that are unchanged
  between the old and new data models.
  """

    def lookup_repository(self, namespace_name, repo_name, kind_filter=None):
        """ Looks up and returns a reference to the repository with the given namespace and name,
        or None if none. """
        repo = model.repository.get_repository(namespace_name, repo_name, kind_filter=kind_filter)
        state = repo.state if repo is not None else None
        return RepositoryReference.for_repo_obj(
            repo,
            namespace_name,
            repo_name,
            repo.namespace_user.stripe_id is None if repo else None,
            state=state,
        )

    def is_existing_disabled_namespace(self, namespace_name):
        """ Returns whether the given namespace exists and is disabled. """
        namespace = model.user.get_namespace_user(namespace_name)
        return namespace is not None and not namespace.enabled

    def is_namespace_enabled(self, namespace_name):
        """ Returns whether the given namespace exists and is enabled. """
        namespace = model.user.get_namespace_user(namespace_name)
        return namespace is not None and namespace.enabled

    def get_derived_image_signature(self, derived_image, signer_name):
        """
    Returns the signature associated with the derived image and a specific signer or None if none.
    """
        try:
            derived_storage = database.DerivedStorageForImage.get(id=derived_image._db_id)
        except database.DerivedStorageForImage.DoesNotExist:
            return None

        storage = derived_storage.derivative
        signature_entry = model.storage.lookup_storage_signature(storage, signer_name)
        if signature_entry is None:
            return None

        return signature_entry.signature

    def set_derived_image_signature(self, derived_image, signer_name, signature):
        """
    Sets the calculated signature for the given derived image and signer to that specified.
    """
        try:
            derived_storage = database.DerivedStorageForImage.get(id=derived_image._db_id)
        except database.DerivedStorageForImage.DoesNotExist:
            return None

        storage = derived_storage.derivative
        signature_entry = model.storage.find_or_create_storage_signature(storage, signer_name)
        signature_entry.signature = signature
        signature_entry.uploading = False
        signature_entry.save()

    def delete_derived_image(self, derived_image):
        """
    Deletes a derived image and all of its storage.
    """
        try:
            derived_storage = database.DerivedStorageForImage.get(id=derived_image._db_id)
        except database.DerivedStorageForImage.DoesNotExist:
            return None

        model.image.delete_derived_storage(derived_storage)

    def set_derived_image_size(self, derived_image, compressed_size):
        """
    Sets the compressed size on the given derived image.
    """
        try:
            derived_storage = database.DerivedStorageForImage.get(id=derived_image._db_id)
        except database.DerivedStorageForImage.DoesNotExist:
            return None

        storage_entry = derived_storage.derivative
        storage_entry.image_size = compressed_size
        storage_entry.uploading = False
        storage_entry.save()

    def get_torrent_info(self, blob):
        """
    Returns the torrent information associated with the given blob or None if none.
    """
        try:
            image_storage = database.ImageStorage.get(id=blob._db_id)
        except database.ImageStorage.DoesNotExist:
            return None

        try:
            torrent_info = model.storage.get_torrent_info(image_storage)
        except model.TorrentInfoDoesNotExist:
            return None

        return TorrentInfo.for_torrent_info(torrent_info)

    def set_torrent_info(self, blob, piece_length, pieces):
        """
    Sets the torrent infomation associated with the given blob to that specified.
    """
        try:
            image_storage = database.ImageStorage.get(id=blob._db_id)
        except database.ImageStorage.DoesNotExist:
            return None

        torrent_info = model.storage.save_torrent_info(image_storage, piece_length, pieces)
        return TorrentInfo.for_torrent_info(torrent_info)

    @abstractmethod
    def lookup_active_repository_tags(self, repository_ref, start_pagination_id, limit):
        pass

    def lookup_cached_active_repository_tags(
        self, model_cache, repository_ref, start_pagination_id, limit
    ):
        """
    Returns a page of active tags in a repository. Note that the tags returned by this method
    are ShallowTag objects, which only contain the tag name. This method will automatically cache
    the result and check the cache before making a call.
    """

        def load_tags():
            tags = self.lookup_active_repository_tags(repository_ref, start_pagination_id, limit)
            return [tag.asdict() for tag in tags]

        tags_cache_key = cache_key.for_active_repo_tags(
            repository_ref._db_id, start_pagination_id, limit
        )
        result = model_cache.retrieve(tags_cache_key, load_tags)

        try:
            return [ShallowTag.from_dict(tag_dict) for tag_dict in result]
        except FromDictionaryException:
            return self.lookup_active_repository_tags(repository_ref, start_pagination_id, limit)

    def get_cached_namespace_region_blacklist(self, model_cache, namespace_name):
        """ Returns a cached set of ISO country codes blacklisted for pulls for the namespace
        or None if the list could not be loaded.
    """

        def load_blacklist():
            restrictions = model.user.list_namespace_geo_restrictions(namespace_name)
            if restrictions is None:
                return None

            return [restriction.restricted_region_iso_code for restriction in restrictions]

        blacklist_cache_key = cache_key.for_namespace_geo_restrictions(namespace_name)
        result = model_cache.retrieve(blacklist_cache_key, load_blacklist)
        if result is None:
            return None

        return set(result)

    def get_cached_repo_blob(self, model_cache, namespace_name, repo_name, blob_digest):
        """
    Returns the blob in the repository with the given digest if any or None if none.
    Caches the result in the caching system.
    """

        def load_blob():
            repository_ref = self.lookup_repository(namespace_name, repo_name)
            if repository_ref is None:
                return None

            blob_found = self.get_repo_blob_by_digest(
                repository_ref, blob_digest, include_placements=True
            )
            if blob_found is None:
                return None

            return blob_found.asdict()

        blob_cache_key = cache_key.for_repository_blob(namespace_name, repo_name, blob_digest, 2)
        blob_dict = model_cache.retrieve(blob_cache_key, load_blob)

        try:
            return Blob.from_dict(blob_dict) if blob_dict is not None else None
        except FromDictionaryException:
            # The data was stale in some way. Simply reload.
            repository_ref = self.lookup_repository(namespace_name, repo_name)
            if repository_ref is None:
                return None

            return self.get_repo_blob_by_digest(
                repository_ref, blob_digest, include_placements=True
            )

    @abstractmethod
    def get_repo_blob_by_digest(self, repository_ref, blob_digest, include_placements=False):
        pass

    def create_blob_upload(self, repository_ref, new_upload_id, location_name, storage_metadata):
        """ Creates a new blob upload and returns a reference. If the blob upload could not be
        created, returns None. """
        repo = model.repository.lookup_repository(repository_ref._db_id)
        if repo is None:
            return None

        try:
            upload_record = model.blob.initiate_upload_for_repo(
                repo, new_upload_id, location_name, storage_metadata
            )
            return BlobUpload.for_upload(upload_record, location_name=location_name)
        except database.Repository.DoesNotExist:
            return None

    def lookup_blob_upload(self, repository_ref, blob_upload_id):
        """ Looks up the blob upload withn the given ID under the specified repository and returns it
        or None if none.
    """
        upload_record = model.blob.get_blob_upload_by_uuid(blob_upload_id)
        if upload_record is None:
            return None

        return BlobUpload.for_upload(upload_record)

    def update_blob_upload(
        self,
        blob_upload,
        uncompressed_byte_count,
        piece_hashes,
        piece_sha_state,
        storage_metadata,
        byte_count,
        chunk_count,
        sha_state,
    ):
        """ Updates the fields of the blob upload to match those given. Returns the updated blob upload
        or None if the record does not exists.
    """
        upload_record = model.blob.get_blob_upload_by_uuid(blob_upload.upload_id)
        if upload_record is None:
            return None

        upload_record.uncompressed_byte_count = uncompressed_byte_count
        upload_record.piece_hashes = piece_hashes
        upload_record.piece_sha_state = piece_sha_state
        upload_record.storage_metadata = storage_metadata
        upload_record.byte_count = byte_count
        upload_record.chunk_count = chunk_count
        upload_record.sha_state = sha_state
        upload_record.save()
        return BlobUpload.for_upload(upload_record)

    def delete_blob_upload(self, blob_upload):
        """ Deletes a blob upload record. """
        upload_record = model.blob.get_blob_upload_by_uuid(blob_upload.upload_id)
        if upload_record is not None:
            upload_record.delete_instance()

    def commit_blob_upload(self, blob_upload, blob_digest_str, blob_expiration_seconds):
        """ Commits the blob upload into a blob and sets an expiration before that blob will be GCed.
    """
        upload_record = model.blob.get_blob_upload_by_uuid(blob_upload.upload_id)
        if upload_record is None:
            return None

        repository_id = upload_record.repository_id

        # Create the blob and temporarily tag it.
        location_obj = model.storage.get_image_location_for_name(blob_upload.location_name)
        blob_record = model.blob.store_blob_record_and_temp_link_in_repo(
            repository_id,
            blob_digest_str,
            location_obj.id,
            blob_upload.byte_count,
            blob_expiration_seconds,
            blob_upload.uncompressed_byte_count,
        )

        # Delete the blob upload.
        upload_record.delete_instance()
        return Blob.for_image_storage(
            blob_record, storage_path=model.storage.get_layer_path(blob_record)
        )

    def mount_blob_into_repository(self, blob, target_repository_ref, expiration_sec):
        """
    Mounts the blob from another repository into the specified target repository, and adds an
    expiration before that blob is automatically GCed. This function is useful during push
    operations if an existing blob from another repository is being pushed. Returns False if
    the mounting fails.
    """
        storage = model.blob.temp_link_blob(
            target_repository_ref._db_id, blob.digest, expiration_sec
        )
        return bool(storage)

    def get_legacy_images(self, repository_ref):
        """
    Returns an iterator of all the LegacyImage's defined in the matching repository.
    """
        repo = model.repository.lookup_repository(repository_ref._db_id)
        if repo is None:
            return None

        all_images = model.image.get_repository_images_without_placements(repo)
        all_images_map = {image.id: image for image in all_images}

        all_tags = model.tag.list_repository_tags(repo.namespace_user.username, repo.name)
        tags_by_image_id = defaultdict(list)
        for tag in all_tags:
            tags_by_image_id[tag.image_id].append(tag)

        return [
            LegacyImage.for_image(image, images_map=all_images_map, tags_map=tags_by_image_id)
            for image in all_images
        ]

    def get_legacy_image(
        self, repository_ref, docker_image_id, include_parents=False, include_blob=False
    ):
        """
    Returns the matching LegacyImages under the matching repository, if any. If none,
    returns None.
    """
        repo = model.repository.lookup_repository(repository_ref._db_id)
        if repo is None:
            return None

        image = model.image.get_image(repository_ref._db_id, docker_image_id)
        if image is None:
            return None

        parent_images_map = None
        if include_parents:
            parent_images = model.image.get_parent_images(
                repo.namespace_user.username, repo.name, image
            )
            parent_images_map = {image.id: image for image in parent_images}

        blob = None
        if include_blob:
            placements = list(model.storage.get_storage_locations(image.storage.uuid))
            blob = Blob.for_image_storage(
                image.storage,
                storage_path=model.storage.get_layer_path(image.storage),
                placements=placements,
            )

        return LegacyImage.for_image(image, images_map=parent_images_map, blob=blob)

    def _get_manifest_local_blobs(
        self, manifest, repo_id, include_placements=False, by_manifest=False
    ):
        parsed = manifest.get_parsed_manifest()
        if parsed is None:
            return None

        local_blob_digests = list(set(parsed.local_blob_digests))
        if not len(local_blob_digests):
            return []

        blob_query = self._lookup_repo_storages_by_content_checksum(
            repo_id, local_blob_digests, by_manifest=by_manifest
        )
        blobs = []
        for image_storage in blob_query:
            placements = None
            if include_placements:
                placements = list(model.storage.get_storage_locations(image_storage.uuid))

            blob = Blob.for_image_storage(
                image_storage,
                storage_path=model.storage.get_layer_path(image_storage),
                placements=placements,
            )
            blobs.append(blob)

        return blobs

    def _list_manifest_layers(
        self, repo_id, parsed, storage, include_placements=False, by_manifest=False
    ):
        """ Returns an *ordered list* of the layers found in the manifest, starting at the base and
        working towards the leaf, including the associated Blob and its placements (if specified).
        Returns None if the manifest could not be parsed and validated.
    """
        assert not parsed.is_manifest_list

        retriever = RepositoryContentRetriever(repo_id, storage)
        requires_empty_blob = parsed.get_requires_empty_layer_blob(retriever)

        storage_map = {}
        blob_digests = list(parsed.local_blob_digests)
        if requires_empty_blob:
            blob_digests.append(EMPTY_LAYER_BLOB_DIGEST)

        if blob_digests:
            blob_query = self._lookup_repo_storages_by_content_checksum(
                repo_id, blob_digests, by_manifest=by_manifest
            )
            storage_map = {blob.content_checksum: blob for blob in blob_query}

        layers = parsed.get_layers(retriever)
        if layers is None:
            logger.error("Could not load layers for manifest `%s`", parsed.digest)
            return None

        manifest_layers = []
        for layer in layers:
            if layer.is_remote:
                manifest_layers.append(ManifestLayer(layer, None))
                continue

            digest_str = str(layer.blob_digest)
            if digest_str not in storage_map:
                logger.error(
                    "Missing digest `%s` for manifest `%s`", layer.blob_digest, parsed.digest
                )
                return None

            image_storage = storage_map[digest_str]
            assert image_storage.cas_path is not None
            assert image_storage.image_size is not None

            placements = None
            if include_placements:
                placements = list(model.storage.get_storage_locations(image_storage.uuid))

            blob = Blob.for_image_storage(
                image_storage,
                storage_path=model.storage.get_layer_path(image_storage),
                placements=placements,
            )
            manifest_layers.append(ManifestLayer(layer, blob))

        return manifest_layers

    def _build_derived(self, derived, verb, varying_metadata, include_placements):
        if derived is None:
            return None

        derived_storage = derived.derivative
        placements = None
        if include_placements:
            placements = list(model.storage.get_storage_locations(derived_storage.uuid))

        blob = Blob.for_image_storage(
            derived_storage,
            storage_path=model.storage.get_layer_path(derived_storage),
            placements=placements,
        )

        return DerivedImage.for_derived_storage(derived, verb, varying_metadata, blob)

    def _build_manifest_for_legacy_image(self, tag_name, legacy_image_row):
        import features

        from app import app, docker_v2_signing_key

        repo = legacy_image_row.repository
        namespace_name = repo.namespace_user.username
        repo_name = repo.name

        # Find the v1 metadata for this image and its parents.
        try:
            parents = model.image.get_parent_images(namespace_name, repo_name, legacy_image_row)
        except model.DataModelException:
            logger.exception(
                "Could not load parent images for legacy image %s", legacy_image_row.id
            )
            return None

        # If the manifest is being generated under the library namespace, then we make its namespace
        # empty.
        manifest_namespace = namespace_name
        if features.LIBRARY_SUPPORT and namespace_name == app.config["LIBRARY_NAMESPACE"]:
            manifest_namespace = ""

        # Create and populate the manifest builder
        builder = DockerSchema1ManifestBuilder(manifest_namespace, repo_name, tag_name)

        # Add the leaf layer
        builder.add_layer(
            legacy_image_row.storage.content_checksum, legacy_image_row.v1_json_metadata
        )
        if legacy_image_row.storage.uploading:
            logger.error("Cannot add an uploading storage row: %s", legacy_image_row.storage.id)
            return None

        for parent_image in parents:
            if parent_image.storage.uploading:
                logger.error("Cannot add an uploading storage row: %s", legacy_image_row.storage.id)
                return None

            builder.add_layer(parent_image.storage.content_checksum, parent_image.v1_json_metadata)

        try:
            built_manifest = builder.build(docker_v2_signing_key)

            # If the generated manifest is greater than the maximum size, regenerate it with
            # intermediate metadata layers stripped down to their bare essentials.
            if len(built_manifest.bytes.as_encoded_str()) > MAXIMUM_GENERATED_MANIFEST_SIZE:
                built_manifest = builder.with_metadata_removed().build(docker_v2_signing_key)

            if len(built_manifest.bytes.as_encoded_str()) > MAXIMUM_GENERATED_MANIFEST_SIZE:
                logger.error("Legacy image is too large to generate manifest")
                return None

            return built_manifest
        except ManifestException as me:
            logger.exception(
                "Got exception when trying to build manifest for legacy image %s", legacy_image_row
            )
            return None

    def _get_shared_storage(self, blob_digest):
        """ Returns an ImageStorage row for the blob digest if it is a globally shared storage. """
        # If the EMPTY_LAYER_BLOB_DIGEST is in the checksums, look it up directly. Since we have
        # so many duplicate copies in the database currently, looking it up bound to a repository
        # can be incredibly slow, and, since it is defined as a globally shared layer, this is extra
        # work we don't need to do.
        if blob_digest == EMPTY_LAYER_BLOB_DIGEST:
            return get_shared_blob(EMPTY_LAYER_BLOB_DIGEST)

        return None

    def _lookup_repo_storages_by_content_checksum(self, repo, checksums, by_manifest=False):
        checksums = set(checksums)

        # Load any shared storages first.
        extra_storages = []
        for checksum in list(checksums):
            shared_storage = self._get_shared_storage(checksum)
            if shared_storage is not None:
                extra_storages.append(shared_storage)
                checksums.remove(checksum)

        found = []
        if checksums:
            found = list(
                model.storage.lookup_repo_storages_by_content_checksum(
                    repo, checksums, by_manifest=by_manifest
                )
            )
        return found + extra_storages
