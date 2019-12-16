# pylint: disable=protected-access
import logging

from contextlib import contextmanager

from peewee import IntegrityError, fn

from data import database
from data import model
from data.database import db_transaction, IMAGE_NOT_SCANNED_ENGINE_VERSION
from data.registry_model.interface import RegistryDataInterface
from data.registry_model.datatypes import (
    Tag,
    Manifest,
    LegacyImage,
    Label,
    SecurityScanStatus,
    Blob,
    RepositoryReference,
    ShallowTag,
    LikelyVulnerableTag,
)
from data.registry_model.shared import SharedModel
from data.registry_model.label_handlers import apply_label_to_manifest
from image.docker.schema1 import ManifestException, DockerSchema1Manifest
from util.validation import is_json


logger = logging.getLogger(__name__)


class PreOCIModel(SharedModel, RegistryDataInterface):
    """
    PreOCIModel implements the data model for the registry API using a database schema before it was
    changed to support the OCI specification.
    """

    def supports_schema2(self, namespace_name):
        """
        Returns whether the implementation of the data interface supports schema 2 format manifests.
        """
        return False

    def get_tag_legacy_image_id(self, repository_ref, tag_name, storage):
        """
        Returns the legacy image ID for the tag with a legacy images in the repository.

        Returns None if None.
        """
        tag = self.get_repo_tag(repository_ref, tag_name, include_legacy_image=True)
        if tag is None:
            return None

        return tag.legacy_image.docker_image_id

    def get_legacy_tags_map(self, repository_ref, storage):
        """
        Returns a map from tag name to its legacy image, for all tags with legacy images in the
        repository.
        """
        tags = self.list_all_active_repository_tags(repository_ref, include_legacy_images=True)
        return {tag.name: tag.legacy_image.docker_image_id for tag in tags}

    def find_matching_tag(self, repository_ref, tag_names):
        """
        Finds an alive tag in the repository matching one of the given tag names and returns it or
        None if none.
        """
        found_tag = model.tag.find_matching_tag(repository_ref._db_id, tag_names)
        assert found_tag is None or not found_tag.hidden
        return Tag.for_repository_tag(found_tag)

    def get_most_recent_tag(self, repository_ref):
        """
        Returns the most recently pushed alive tag in the repository, if any.

        If none, returns None.
        """
        found_tag = model.tag.get_most_recent_tag(repository_ref._db_id)
        assert found_tag is None or not found_tag.hidden
        return Tag.for_repository_tag(found_tag)

    def get_manifest_for_tag(self, tag, backfill_if_necessary=False, include_legacy_image=False):
        """
        Returns the manifest associated with the given tag.
        """
        try:
            tag_manifest = database.TagManifest.get(tag_id=tag._db_id)
        except database.TagManifest.DoesNotExist:
            if backfill_if_necessary:
                return self.backfill_manifest_for_tag(tag)

            return None

        return Manifest.for_tag_manifest(tag_manifest)

    def lookup_manifest_by_digest(
        self,
        repository_ref,
        manifest_digest,
        allow_dead=False,
        include_legacy_image=False,
        require_available=False,
    ):
        """
        Looks up the manifest with the given digest under the given repository and returns it or
        None if none.
        """
        repo = model.repository.lookup_repository(repository_ref._db_id)
        if repo is None:
            return None

        try:
            tag_manifest = model.tag.load_manifest_by_digest(
                repo.namespace_user.username, repo.name, manifest_digest, allow_dead=allow_dead
            )
        except model.tag.InvalidManifestException:
            return None

        legacy_image = None
        if include_legacy_image:
            legacy_image = self.get_legacy_image(
                repository_ref, tag_manifest.tag.image.docker_image_id, include_parents=True
            )

        return Manifest.for_tag_manifest(tag_manifest, legacy_image)

    def create_manifest_and_retarget_tag(
        self, repository_ref, manifest_interface_instance, tag_name, storage, raise_on_error=False
    ):
        """
        Creates a manifest in a repository, adding all of the necessary data in the model.

        The `manifest_interface_instance` parameter must be an instance of the manifest
        interface as returned by the image/docker package.

        Note that all blobs referenced by the manifest must exist under the repository or this
        method will fail and return None.

        Returns a reference to the (created manifest, tag) or (None, None) on error.
        """
        # NOTE: Only Schema1 is supported by the pre_oci_model.
        assert isinstance(manifest_interface_instance, DockerSchema1Manifest)
        if not manifest_interface_instance.layers:
            return None, None

        # Ensure all the blobs in the manifest exist.
        digests = manifest_interface_instance.checksums
        query = self._lookup_repo_storages_by_content_checksum(repository_ref._db_id, digests)
        blob_map = {s.content_checksum: s for s in query}
        for layer in manifest_interface_instance.layers:
            digest_str = str(layer.digest)
            if digest_str not in blob_map:
                return None, None

        # Lookup all the images and their parent images (if any) inside the manifest.
        # This will let us know which v1 images we need to synthesize and which ones are invalid.
        docker_image_ids = list(manifest_interface_instance.legacy_image_ids)
        images_query = model.image.lookup_repository_images(repository_ref._db_id, docker_image_ids)
        image_storage_map = {i.docker_image_id: i.storage for i in images_query}

        # Rewrite any v1 image IDs that do not match the checksum in the database.
        try:
            rewritten_images = manifest_interface_instance.rewrite_invalid_image_ids(
                image_storage_map
            )
            rewritten_images = list(rewritten_images)
            parent_image_map = {}

            for rewritten_image in rewritten_images:
                if not rewritten_image.image_id in image_storage_map:
                    parent_image = None
                    if rewritten_image.parent_image_id:
                        parent_image = parent_image_map.get(rewritten_image.parent_image_id)
                        if parent_image is None:
                            parent_image = model.image.get_image(
                                repository_ref._db_id, rewritten_image.parent_image_id
                            )
                            if parent_image is None:
                                return None, None

                    synthesized = model.image.synthesize_v1_image(
                        repository_ref._db_id,
                        blob_map[rewritten_image.content_checksum].id,
                        blob_map[rewritten_image.content_checksum].image_size,
                        rewritten_image.image_id,
                        rewritten_image.created,
                        rewritten_image.comment,
                        rewritten_image.command,
                        rewritten_image.compat_json,
                        parent_image,
                    )

                    parent_image_map[rewritten_image.image_id] = synthesized
        except ManifestException:
            logger.exception("exception when rewriting v1 metadata")
            return None, None

        # Store the manifest pointing to the tag.
        leaf_layer_id = rewritten_images[-1].image_id
        tag_manifest, newly_created = model.tag.store_tag_manifest_for_repo(
            repository_ref._db_id, tag_name, manifest_interface_instance, leaf_layer_id, blob_map
        )

        manifest = Manifest.for_tag_manifest(tag_manifest)

        # Save the labels on the manifest.
        repo_tag = tag_manifest.tag
        if newly_created:
            has_labels = False
            with self.batch_create_manifest_labels(manifest) as add_label:
                if add_label is None:
                    return None, None

                for key, value in manifest_interface_instance.layers[
                    -1
                ].v1_metadata.labels.items():
                    # NOTE: There can technically be empty label keys via Dockerfile's. We ignore any
                    # such `labels`, as they don't really mean anything.
                    if not key:
                        continue

                    media_type = "application/json" if is_json(value) else "text/plain"
                    add_label(key, value, "manifest", media_type)
                    has_labels = True

            # Reload the tag in case any updates were applied.
            if has_labels:
                repo_tag = database.RepositoryTag.get(id=repo_tag.id)

        return manifest, Tag.for_repository_tag(repo_tag)

    def create_manifest_label(self, manifest, key, value, source_type_name, media_type_name=None):
        """
        Creates a label on the manifest with the given key and value.
        """
        try:
            tag_manifest = database.TagManifest.get(id=manifest._db_id)
        except database.TagManifest.DoesNotExist:
            return None

        label_data = dict(
            key=key, value=value, source_type_name=source_type_name, media_type_name=media_type_name
        )

        with db_transaction():
            # Create the label itself.
            label = model.label.create_manifest_label(
                tag_manifest, key, value, source_type_name, media_type_name
            )

            # Apply any changes to the manifest that the label prescribes.
            apply_label_to_manifest(label_data, manifest, self)

        return Label.for_label(label)

    @contextmanager
    def batch_create_manifest_labels(self, manifest):
        """
        Returns a context manager for batch creation of labels on a manifest.

        Can raise InvalidLabelKeyException or InvalidMediaTypeException depending on the validation
        errors.
        """
        try:
            tag_manifest = database.TagManifest.get(id=manifest._db_id)
        except database.TagManifest.DoesNotExist:
            yield None
            return

        labels_to_add = []

        def add_label(key, value, source_type_name, media_type_name=None):
            labels_to_add.append(
                dict(
                    key=key,
                    value=value,
                    source_type_name=source_type_name,
                    media_type_name=media_type_name,
                )
            )

        yield add_label

        # TODO: make this truly batch once we've fully transitioned to V2_2 and no longer need
        # the mapping tables.
        for label in labels_to_add:
            with db_transaction():
                # Create the label itself.
                model.label.create_manifest_label(tag_manifest, **label)

                # Apply any changes to the manifest that the label prescribes.
                apply_label_to_manifest(label, manifest, self)

    def list_manifest_labels(self, manifest, key_prefix=None):
        """
        Returns all labels found on the manifest.

        If specified, the key_prefix will filter the labels returned to those keys that start with
        the given prefix.
        """
        labels = model.label.list_manifest_labels(manifest._db_id, prefix_filter=key_prefix)
        return [Label.for_label(l) for l in labels]

    def get_manifest_label(self, manifest, label_uuid):
        """
        Returns the label with the specified UUID on the manifest or None if none.
        """
        return Label.for_label(model.label.get_manifest_label(label_uuid, manifest._db_id))

    def delete_manifest_label(self, manifest, label_uuid):
        """
        Delete the label with the specified UUID on the manifest.

        Returns the label deleted or None if none.
        """
        return Label.for_label(model.label.delete_manifest_label(label_uuid, manifest._db_id))

    def lookup_active_repository_tags(self, repository_ref, start_pagination_id, limit):
        """
        Returns a page of actvie tags in a repository.

        Note that the tags returned by this method are ShallowTag objects, which only contain the
        tag name.
        """
        tags = model.tag.list_active_repo_tags(
            repository_ref._db_id, include_images=False, start_id=start_pagination_id, limit=limit
        )
        return [ShallowTag.for_repository_tag(tag) for tag in tags]

    def list_all_active_repository_tags(self, repository_ref, include_legacy_images=False):
        """
        Returns a list of all the active tags in the repository.

        Note that this is a *HEAVY* operation on repositories with a lot of tags, and should only be
        used for testing or where other more specific operations are not possible.
        """
        if not include_legacy_images:
            tags = model.tag.list_active_repo_tags(repository_ref._db_id, include_images=False)
            return [Tag.for_repository_tag(tag) for tag in tags]

        tags = model.tag.list_active_repo_tags(repository_ref._db_id)
        return [
            Tag.for_repository_tag(
                tag,
                legacy_image=LegacyImage.for_image(tag.image),
                manifest_digest=(tag.tagmanifest.digest if hasattr(tag, "tagmanifest") else None),
            )
            for tag in tags
        ]

    def list_repository_tag_history(
        self,
        repository_ref,
        page=1,
        size=100,
        specific_tag_name=None,
        active_tags_only=False,
        since_time_ms=None,
    ):
        """
        Returns the history of all tags in the repository (unless filtered).

        This includes tags that have been made in-active due to newer versions of those tags coming
        into service.
        """

        # Only available on OCI model
        if since_time_ms is not None:
            raise NotImplementedError

        tags, manifest_map, has_more = model.tag.list_repository_tag_history(
            repository_ref._db_id, page, size, specific_tag_name, active_tags_only
        )
        return (
            [
                Tag.for_repository_tag(
                    tag, manifest_map.get(tag.id), legacy_image=LegacyImage.for_image(tag.image)
                )
                for tag in tags
            ],
            has_more,
        )

    def has_expired_tag(self, repository_ref, tag_name):
        """
        Returns true if and only if the repository contains a tag with the given name that is
        expired.
        """
        try:
            model.tag.get_expired_tag_in_repo(repository_ref._db_id, tag_name)
            return True
        except database.RepositoryTag.DoesNotExist:
            return False

    def get_most_recent_tag_lifetime_start(self, repository_refs):
        """
        Returns a map from repository ID to the last modified time (in s) for each repository in the
        given repository reference list.
        """
        if not repository_refs:
            return {}

        tuples = (
            database.RepositoryTag.select(
                database.RepositoryTag.repository, fn.Max(database.RepositoryTag.lifetime_start_ts)
            )
            .where(database.RepositoryTag.repository << [r.id for r in repository_refs])
            .group_by(database.RepositoryTag.repository)
            .tuples()
        )

        return {repo_id: seconds for repo_id, seconds in tuples}

    def get_repo_tag(self, repository_ref, tag_name, include_legacy_image=False):
        """
        Returns the latest, *active* tag found in the repository, with the matching name or None if
        none.
        """
        assert isinstance(tag_name, str)
        tag = model.tag.get_active_tag_for_repo(repository_ref._db_id, tag_name)
        if tag is None:
            return None

        legacy_image = LegacyImage.for_image(tag.image) if include_legacy_image else None
        tag_manifest = model.tag.get_tag_manifest(tag)
        manifest_digest = tag_manifest.digest if tag_manifest else None
        return Tag.for_repository_tag(
            tag, legacy_image=legacy_image, manifest_digest=manifest_digest
        )

    def retarget_tag(
        self,
        repository_ref,
        tag_name,
        manifest_or_legacy_image,
        storage,
        legacy_manifest_key,
        is_reversion=False,
    ):
        """
        Creates, updates or moves a tag to a new entry in history, pointing to the manifest or
        legacy image specified.

        If is_reversion is set to True, this operation is considered a reversion over a previous tag
        move operation. Returns the updated Tag or None on error.
        """
        # TODO: unify this.
        assert legacy_manifest_key is not None
        if not is_reversion:
            if isinstance(manifest_or_legacy_image, Manifest):
                raise NotImplementedError("Not yet implemented")
            else:
                model.tag.create_or_update_tag_for_repo(
                    repository_ref._db_id, tag_name, manifest_or_legacy_image.docker_image_id
                )
        else:
            if isinstance(manifest_or_legacy_image, Manifest):
                model.tag.restore_tag_to_manifest(
                    repository_ref._db_id, tag_name, manifest_or_legacy_image.digest
                )
            else:
                model.tag.restore_tag_to_image(
                    repository_ref._db_id, tag_name, manifest_or_legacy_image.docker_image_id
                )

        # Generate a manifest for the tag, if necessary.
        tag = self.get_repo_tag(repository_ref, tag_name, include_legacy_image=True)
        if tag is None:
            return None

        self.backfill_manifest_for_tag(tag)
        return tag

    def delete_tag(self, repository_ref, tag_name):
        """
        Deletes the latest, *active* tag with the given name in the repository.
        """
        repo = model.repository.lookup_repository(repository_ref._db_id)
        if repo is None:
            return None

        deleted_tag = model.tag.delete_tag(repo.namespace_user.username, repo.name, tag_name)
        return Tag.for_repository_tag(deleted_tag)

    def delete_tags_for_manifest(self, manifest):
        """
        Deletes all tags pointing to the given manifest, making the manifest inaccessible for
        pulling.

        Returns the tags deleted, if any. Returns None on error.
        """
        try:
            tagmanifest = database.TagManifest.get(id=manifest._db_id)
        except database.TagManifest.DoesNotExist:
            return None

        namespace_name = tagmanifest.tag.repository.namespace_user.username
        repo_name = tagmanifest.tag.repository.name
        tags = model.tag.delete_manifest_by_digest(namespace_name, repo_name, manifest.digest)
        return [Tag.for_repository_tag(tag) for tag in tags]

    def change_repository_tag_expiration(self, tag, expiration_date):
        """
        Sets the expiration date of the tag under the matching repository to that given.

        If the expiration date is None, then the tag will not expire. Returns a tuple of the
        previous expiration timestamp in seconds (if any), and whether the operation succeeded.
        """
        try:
            tag_obj = database.RepositoryTag.get(id=tag._db_id)
        except database.RepositoryTag.DoesNotExist:
            return (None, False)

        return model.tag.change_tag_expiration(tag_obj, expiration_date)

    def get_legacy_images_owned_by_tag(self, tag):
        """
        Returns all legacy images *solely owned and used* by the given tag.
        """
        try:
            tag_obj = database.RepositoryTag.get(id=tag._db_id)
        except database.RepositoryTag.DoesNotExist:
            return None

        # Collect the IDs of all images that the tag uses.
        tag_image_ids = set()
        tag_image_ids.add(tag_obj.image.id)
        tag_image_ids.update(tag_obj.image.ancestor_id_list())

        # Remove any images shared by other tags.
        for current_tag in model.tag.list_active_repo_tags(tag_obj.repository_id):
            if current_tag == tag_obj:
                continue

            tag_image_ids.discard(current_tag.image.id)
            tag_image_ids = tag_image_ids.difference(current_tag.image.ancestor_id_list())
            if not tag_image_ids:
                return []

        if not tag_image_ids:
            return []

        # Load the images we need to return.
        images = database.Image.select().where(database.Image.id << list(tag_image_ids))
        all_image_ids = set()
        for image in images:
            all_image_ids.add(image.id)
            all_image_ids.update(image.ancestor_id_list())

        # Build a map of all the images and their parents.
        images_map = {}
        all_images = database.Image.select().where(database.Image.id << list(all_image_ids))
        for image in all_images:
            images_map[image.id] = image

        return [LegacyImage.for_image(image, images_map=images_map) for image in images]

    def get_security_status(self, manifest_or_legacy_image):
        """
        Returns the security status for the given manifest or legacy image or None if none.
        """
        image = None

        if isinstance(manifest_or_legacy_image, Manifest):
            try:
                tag_manifest = database.TagManifest.get(id=manifest_or_legacy_image._db_id)
                image = tag_manifest.tag.image
            except database.TagManifest.DoesNotExist:
                return None
        else:
            try:
                image = database.Image.get(id=manifest_or_legacy_image._db_id)
            except database.Image.DoesNotExist:
                return None

        if image.security_indexed_engine is not None and image.security_indexed_engine >= 0:
            return (
                SecurityScanStatus.SCANNED if image.security_indexed else SecurityScanStatus.FAILED
            )

        return SecurityScanStatus.QUEUED

    def reset_security_status(self, manifest_or_legacy_image):
        """
        Resets the security status for the given manifest or legacy image, ensuring that it will get
        re-indexed.
        """
        image = None

        if isinstance(manifest_or_legacy_image, Manifest):
            try:
                tag_manifest = database.TagManifest.get(id=manifest_or_legacy_image._db_id)
                image = tag_manifest.tag.image
            except database.TagManifest.DoesNotExist:
                return None
        else:
            try:
                image = database.Image.get(id=manifest_or_legacy_image._db_id)
            except database.Image.DoesNotExist:
                return None

        assert image
        image.security_indexed = False
        image.security_indexed_engine = IMAGE_NOT_SCANNED_ENGINE_VERSION
        image.save()

    def backfill_manifest_for_tag(self, tag):
        """
        Backfills a manifest for the V1 tag specified. If a manifest already exists for the tag,
        returns that manifest.

        NOTE: This method will only be necessary until we've completed the backfill, at which point
        it should be removed.
        """
        # Ensure that there isn't already a manifest for the tag.
        tag_manifest = model.tag.get_tag_manifest(tag._db_id)
        if tag_manifest is not None:
            return Manifest.for_tag_manifest(tag_manifest)

        # Create the manifest.
        try:
            tag_obj = database.RepositoryTag.get(id=tag._db_id)
        except database.RepositoryTag.DoesNotExist:
            return None

        assert not tag_obj.hidden

        repo = tag_obj.repository

        # Write the manifest to the DB.
        manifest = self._build_manifest_for_legacy_image(tag_obj.name, tag_obj.image)
        if manifest is None:
            return None

        blob_query = self._lookup_repo_storages_by_content_checksum(repo, manifest.checksums)
        storage_map = {blob.content_checksum: blob.id for blob in blob_query}
        try:
            tag_manifest = model.tag.associate_generated_tag_manifest_with_tag(
                tag_obj, manifest, storage_map
            )
            assert tag_manifest
        except IntegrityError:
            tag_manifest = model.tag.get_tag_manifest(tag_obj)

        return Manifest.for_tag_manifest(tag_manifest)

    def list_manifest_layers(self, manifest, storage, include_placements=False):
        try:
            tag_manifest = database.TagManifest.get(id=manifest._db_id)
        except database.TagManifest.DoesNotExist:
            logger.exception("Could not find tag manifest for manifest `%s`", manifest._db_id)
            return None

        try:
            parsed = manifest.get_parsed_manifest()
        except ManifestException:
            logger.exception("Could not parse and validate manifest `%s`", manifest._db_id)
            return None

        repo_ref = RepositoryReference.for_id(tag_manifest.tag.repository_id)
        return self.list_parsed_manifest_layers(repo_ref, parsed, storage, include_placements)

    def lookup_derived_image(
        self, manifest, verb, storage, varying_metadata=None, include_placements=False
    ):
        """
        Looks up the derived image for the given manifest, verb and optional varying metadata and
        returns it or None if none.
        """
        try:
            tag_manifest = database.TagManifest.get(id=manifest._db_id)
        except database.TagManifest.DoesNotExist:
            logger.exception("Could not find tag manifest for manifest `%s`", manifest._db_id)
            return None

        repo_image = tag_manifest.tag.image
        derived = model.image.find_derived_storage_for_image(repo_image, verb, varying_metadata)
        return self._build_derived(derived, verb, varying_metadata, include_placements)

    def lookup_or_create_derived_image(
        self,
        manifest,
        verb,
        storage_location,
        storage,
        varying_metadata=None,
        include_placements=False,
    ):
        """
        Looks up the derived image for the given maniest, verb and optional varying metadata and
        returns it.

        If none exists, a new derived image is created.
        """
        try:
            tag_manifest = database.TagManifest.get(id=manifest._db_id)
        except database.TagManifest.DoesNotExist:
            logger.exception("Could not find tag manifest for manifest `%s`", manifest._db_id)
            return None

        repo_image = tag_manifest.tag.image
        derived = model.image.find_or_create_derived_storage(
            repo_image, verb, storage_location, varying_metadata
        )
        return self._build_derived(derived, verb, varying_metadata, include_placements)

    def set_tags_expiration_for_manifest(self, manifest, expiration_sec):
        """
        Sets the expiration on all tags that point to the given manifest to that specified.
        """
        try:
            tag_manifest = database.TagManifest.get(id=manifest._db_id)
        except database.TagManifest.DoesNotExist:
            return

        model.tag.set_tag_expiration_for_manifest(tag_manifest, expiration_sec)

    def get_schema1_parsed_manifest(self, manifest, namespace_name, repo_name, tag_name, storage):
        """
        Returns the schema 1 version of this manifest, or None if none.
        """
        try:
            return manifest.get_parsed_manifest()
        except ManifestException:
            return None

    def convert_manifest(
        self, manifest, namespace_name, repo_name, tag_name, allowed_mediatypes, storage
    ):
        try:
            parsed = manifest.get_parsed_manifest()
        except ManifestException:
            return None

        try:
            return parsed.convert_manifest(
                allowed_mediatypes, namespace_name, repo_name, tag_name, None
            )
        except ManifestException:
            return None

    def create_manifest_with_temp_tag(
        self, repository_ref, manifest_interface_instance, expiration_sec, storage
    ):
        """
        Creates a manifest under the repository and sets a temporary tag to point to it.

        Returns the manifest object created or None on error.
        """
        raise NotImplementedError("Unsupported in pre OCI model")

    def get_repo_blob_by_digest(self, repository_ref, blob_digest, include_placements=False):
        """
        Returns the blob in the repository with the given digest, if any or None if none.

        Note that there may be multiple records in the same repository for the same blob digest, so
        the return value of this function may change.
        """
        image_storage = self._get_shared_storage(blob_digest)
        if image_storage is None:
            try:
                image_storage = model.blob.get_repository_blob_by_digest(
                    repository_ref._db_id, blob_digest
                )
            except model.BlobDoesNotExist:
                return None

        assert image_storage.cas_path is not None

        placements = None
        if include_placements:
            placements = list(model.storage.get_storage_locations(image_storage.uuid))

        return Blob.for_image_storage(
            image_storage,
            storage_path=model.storage.get_layer_path(image_storage),
            placements=placements,
        )

    def list_parsed_manifest_layers(
        self, repository_ref, parsed_manifest, storage, include_placements=False
    ):
        """
        Returns an *ordered list* of the layers found in the parsed manifest, starting at the base
        and working towards the leaf, including the associated Blob and its placements (if
        specified).
        """
        return self._list_manifest_layers(
            repository_ref._db_id, parsed_manifest, storage, include_placements=include_placements
        )

    def get_manifest_local_blobs(self, manifest, include_placements=False):
        """
        Returns the set of local blobs for the given manifest or None if none.
        """
        try:
            tag_manifest = database.TagManifest.get(id=manifest._db_id)
        except database.TagManifest.DoesNotExist:
            return None

        return self._get_manifest_local_blobs(
            manifest, tag_manifest.tag.repository_id, include_placements
        )

    def yield_tags_for_vulnerability_notification(self, layer_id_pairs):
        """
        Yields tags that contain one (or more) of the given layer ID pairs, in repositories which
        have been registered for vulnerability_found notifications.

        Returns an iterator of LikelyVulnerableTag instances.
        """
        event = database.ExternalNotificationEvent.get(name="vulnerability_found")

        def filter_notifying_repos(query):
            return model.tag.filter_has_repository_event(query, event)

        def filter_and_order(query):
            return model.tag.filter_tags_have_repository_event(query, event)

        # Find the matching tags.
        tags = model.tag.get_matching_tags_for_images(
            layer_id_pairs,
            selections=[database.RepositoryTag, database.Image, database.ImageStorage],
            filter_images=filter_notifying_repos,
            filter_tags=filter_and_order,
        )
        for tag in tags:
            yield LikelyVulnerableTag.for_repository_tag(tag, tag.repository)


pre_oci_model = PreOCIModel()
