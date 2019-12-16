# pylint: disable=protected-access
import logging

from contextlib import contextmanager
from peewee import fn

from data import database
from data import model
from data.model import oci, DataModelException
from data.model.oci.retriever import RepositoryContentRetriever
from data.database import db_transaction, Image, IMAGE_NOT_SCANNED_ENGINE_VERSION
from data.registry_model.interface import RegistryDataInterface
from data.registry_model.datatypes import (
    Tag,
    Manifest,
    LegacyImage,
    Label,
    SecurityScanStatus,
    Blob,
    ShallowTag,
    LikelyVulnerableTag,
)
from data.registry_model.shared import SharedModel
from data.registry_model.label_handlers import apply_label_to_manifest
from image.docker import ManifestException
from image.docker.schema1 import DOCKER_SCHEMA1_CONTENT_TYPES
from image.docker.schema2 import DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE


logger = logging.getLogger(__name__)


class OCIModel(SharedModel, RegistryDataInterface):
    """
    OCIModel implements the data model for the registry API using a database schema after it was
    changed to support the OCI specification.
    """

    def __init__(self, oci_model_only=True):
        self.oci_model_only = oci_model_only

    def supports_schema2(self, namespace_name):
        """
        Returns whether the implementation of the data interface supports schema 2 format manifests.
        """
        return True

    def get_tag_legacy_image_id(self, repository_ref, tag_name, storage):
        """
        Returns the legacy image ID for the tag with a legacy images in the repository.

        Returns None if None.
        """
        tag = self.get_repo_tag(repository_ref, tag_name, include_legacy_image=True)
        if tag is None:
            return None

        if tag.legacy_image_if_present is not None:
            return tag.legacy_image_if_present.docker_image_id

        if tag.manifest.media_type == DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE:
            # See if we can lookup a schema1 legacy image.
            v1_compatible = self.get_schema1_parsed_manifest(tag.manifest, "", "", "", storage)
            if v1_compatible is not None:
                return v1_compatible.leaf_layer_v1_image_id

        return None

    def get_legacy_tags_map(self, repository_ref, storage):
        """
        Returns a map from tag name to its legacy image ID, for all tags with legacy images in the
        repository.

        Note that this can be a *very* heavy operation.
        """
        tags = oci.tag.list_alive_tags(repository_ref._db_id)
        legacy_images_map = oci.tag.get_legacy_images_for_tags(tags)

        tags_map = {}
        for tag in tags:
            legacy_image = legacy_images_map.get(tag.id)
            if legacy_image is not None:
                tags_map[tag.name] = legacy_image.docker_image_id
            else:
                manifest = Manifest.for_manifest(tag.manifest, None)
                if (
                    legacy_image is None
                    and manifest.media_type == DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE
                ):
                    # See if we can lookup a schema1 legacy image.
                    v1_compatible = self.get_schema1_parsed_manifest(manifest, "", "", "", storage)
                    if v1_compatible is not None:
                        v1_id = v1_compatible.leaf_layer_v1_image_id
                        if v1_id is not None:
                            tags_map[tag.name] = v1_id

        return tags_map

    def _get_legacy_compatible_image_for_manifest(self, manifest, storage):
        # Check for a legacy image directly on the manifest.
        if manifest.media_type != DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE:
            return oci.shared.get_legacy_image_for_manifest(manifest._db_id)

        # Otherwise, lookup a legacy image associated with the v1-compatible manifest
        # in the list.
        try:
            manifest_obj = database.Manifest.get(id=manifest._db_id)
        except database.Manifest.DoesNotExist:
            logger.exception("Could not find manifest for manifest `%s`", manifest._db_id)
            return None

        # See if we can lookup a schema1 legacy image.
        v1_compatible = self.get_schema1_parsed_manifest(manifest, "", "", "", storage)
        if v1_compatible is None:
            return None

        v1_id = v1_compatible.leaf_layer_v1_image_id
        if v1_id is None:
            return None

        return model.image.get_image(manifest_obj.repository_id, v1_id)

    def find_matching_tag(self, repository_ref, tag_names):
        """
        Finds an alive tag in the repository matching one of the given tag names and returns it or
        None if none.
        """
        found_tag = oci.tag.find_matching_tag(repository_ref._db_id, tag_names)
        assert found_tag is None or not found_tag.hidden
        return Tag.for_tag(found_tag)

    def get_most_recent_tag(self, repository_ref):
        """
        Returns the most recently pushed alive tag in the repository, if any.

        If none, returns None.
        """
        found_tag = oci.tag.get_most_recent_tag(repository_ref._db_id)
        assert found_tag is None or not found_tag.hidden
        return Tag.for_tag(found_tag)

    def get_manifest_for_tag(self, tag, backfill_if_necessary=False, include_legacy_image=False):
        """
        Returns the manifest associated with the given tag.
        """
        legacy_image = None
        if include_legacy_image:
            legacy_image = oci.shared.get_legacy_image_for_manifest(tag._manifest)

        return Manifest.for_manifest(tag._manifest, LegacyImage.for_image(legacy_image))

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
        manifest = oci.manifest.lookup_manifest(
            repository_ref._db_id,
            manifest_digest,
            allow_dead=allow_dead,
            require_available=require_available,
        )
        if manifest is None:
            return None

        legacy_image = None
        if include_legacy_image:
            try:
                legacy_image_id = database.ManifestLegacyImage.get(
                    manifest=manifest
                ).image.docker_image_id
                legacy_image = self.get_legacy_image(
                    repository_ref, legacy_image_id, include_parents=True
                )
            except database.ManifestLegacyImage.DoesNotExist:
                pass

        return Manifest.for_manifest(manifest, legacy_image)

    def create_manifest_label(self, manifest, key, value, source_type_name, media_type_name=None):
        """
        Creates a label on the manifest with the given key and value.
        """
        label_data = dict(
            key=key, value=value, source_type_name=source_type_name, media_type_name=media_type_name
        )

        # Create the label itself.
        label = oci.label.create_manifest_label(
            manifest._db_id,
            key,
            value,
            source_type_name,
            media_type_name,
            adjust_old_model=not self.oci_model_only,
        )
        if label is None:
            return None

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
        for label_data in labels_to_add:
            with db_transaction():
                # Create the label itself.
                oci.label.create_manifest_label(manifest._db_id, **label_data)

                # Apply any changes to the manifest that the label prescribes.
                apply_label_to_manifest(label_data, manifest, self)

    def list_manifest_labels(self, manifest, key_prefix=None):
        """
        Returns all labels found on the manifest.

        If specified, the key_prefix will filter the labels returned to those keys that start with
        the given prefix.
        """
        labels = oci.label.list_manifest_labels(manifest._db_id, prefix_filter=key_prefix)
        return [Label.for_label(l) for l in labels]

    def get_manifest_label(self, manifest, label_uuid):
        """
        Returns the label with the specified UUID on the manifest or None if none.
        """
        return Label.for_label(oci.label.get_manifest_label(label_uuid, manifest._db_id))

    def delete_manifest_label(self, manifest, label_uuid):
        """
        Delete the label with the specified UUID on the manifest.

        Returns the label deleted or None if none.
        """
        return Label.for_label(oci.label.delete_manifest_label(label_uuid, manifest._db_id))

    def lookup_active_repository_tags(self, repository_ref, start_pagination_id, limit):
        """
        Returns a page of actvie tags in a repository.

        Note that the tags returned by this method are ShallowTag objects, which only contain the
        tag name.
        """
        tags = oci.tag.lookup_alive_tags_shallow(repository_ref._db_id, start_pagination_id, limit)
        return [ShallowTag.for_tag(tag) for tag in tags]

    def list_all_active_repository_tags(self, repository_ref, include_legacy_images=False):
        """
        Returns a list of all the active tags in the repository.

        Note that this is a *HEAVY* operation on repositories with a lot of tags, and should only be
        used for testing or where other more specific operations are not possible.
        """
        tags = list(oci.tag.list_alive_tags(repository_ref._db_id))
        legacy_images_map = {}
        if include_legacy_images:
            legacy_images_map = oci.tag.get_legacy_images_for_tags(tags)

        return [
            Tag.for_tag(tag, legacy_image=LegacyImage.for_image(legacy_images_map.get(tag.id)))
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
        tags, has_more = oci.tag.list_repository_tag_history(
            repository_ref._db_id, page, size, specific_tag_name, active_tags_only, since_time_ms
        )

        # TODO: do we need legacy images here?
        legacy_images_map = oci.tag.get_legacy_images_for_tags(tags)
        return (
            [
                Tag.for_tag(tag, LegacyImage.for_image(legacy_images_map.get(tag.id)))
                for tag in tags
            ],
            has_more,
        )

    def has_expired_tag(self, repository_ref, tag_name):
        """
        Returns true if and only if the repository contains a tag with the given name that is
        expired.
        """
        return bool(oci.tag.get_expired_tag(repository_ref._db_id, tag_name))

    def get_most_recent_tag_lifetime_start(self, repository_refs):
        """
        Returns a map from repository ID to the last modified time (in s) for each repository in the
        given repository reference list.
        """
        if not repository_refs:
            return {}

        toSeconds = lambda ms: ms / 1000 if ms is not None else None
        last_modified = oci.tag.get_most_recent_tag_lifetime_start([r.id for r in repository_refs])

        return {repo_id: toSeconds(ms) for repo_id, ms in list(last_modified.items())}

    def get_repo_tag(self, repository_ref, tag_name, include_legacy_image=False):
        """
        Returns the latest, *active* tag found in the repository, with the matching name or None if
        none.
        """
        assert isinstance(tag_name, str)

        tag = oci.tag.get_tag(repository_ref._db_id, tag_name)
        if tag is None:
            return None

        legacy_image = None
        if include_legacy_image:
            legacy_images = oci.tag.get_legacy_images_for_tags([tag])
            legacy_image = legacy_images.get(tag.id)

        return Tag.for_tag(tag, legacy_image=LegacyImage.for_image(legacy_image))

    def create_manifest_and_retarget_tag(
        self, repository_ref, manifest_interface_instance, tag_name, storage, raise_on_error=False
    ):
        """
        Creates a manifest in a repository, adding all of the necessary data in the model.

        The `manifest_interface_instance` parameter must be an instance of the manifest
        interface as returned by the image/docker package.

        Note that all blobs referenced by the manifest must exist under the repository or this
        method will fail and return None.

        Returns a reference to the (created manifest, tag) or (None, None) on error, unless
        raise_on_error is set to True, in which case a CreateManifestException may also be
        raised.
        """
        # Get or create the manifest itself.
        created_manifest = oci.manifest.get_or_create_manifest(
            repository_ref._db_id,
            manifest_interface_instance,
            storage,
            for_tagging=True,
            raise_on_error=raise_on_error,
        )
        if created_manifest is None:
            return (None, None)

        # Re-target the tag to it.
        tag = oci.tag.retarget_tag(
            tag_name, created_manifest.manifest, adjust_old_model=not self.oci_model_only
        )
        if tag is None:
            return (None, None)

        legacy_image = oci.shared.get_legacy_image_for_manifest(created_manifest.manifest)
        li = LegacyImage.for_image(legacy_image)
        wrapped_manifest = Manifest.for_manifest(created_manifest.manifest, li)

        # Apply any labels that should modify the created tag.
        if created_manifest.labels_to_apply:
            for key, value in created_manifest.labels_to_apply.items():
                apply_label_to_manifest(dict(key=key, value=value), wrapped_manifest, self)

            # Reload the tag in case any updates were applied.
            tag = database.Tag.get(id=tag.id)

        return (wrapped_manifest, Tag.for_tag(tag, li))

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
        assert legacy_manifest_key is not None
        manifest_id = manifest_or_legacy_image._db_id
        if isinstance(manifest_or_legacy_image, LegacyImage):
            # If a legacy image was required, build a new manifest for it and move the tag to that.
            try:
                image_row = database.Image.get(id=manifest_or_legacy_image._db_id)
            except database.Image.DoesNotExist:
                return None

            manifest_instance = self._build_manifest_for_legacy_image(tag_name, image_row)
            if manifest_instance is None:
                return None

            created = oci.manifest.get_or_create_manifest(
                repository_ref._db_id, manifest_instance, storage
            )
            if created is None:
                return None

            manifest_id = created.manifest.id
        else:
            # If the manifest is a schema 1 manifest and its tag name does not match that
            # specified, then we need to create a new manifest, but with that tag name.
            if manifest_or_legacy_image.media_type in DOCKER_SCHEMA1_CONTENT_TYPES:
                try:
                    parsed = manifest_or_legacy_image.get_parsed_manifest()
                except ManifestException:
                    logger.exception(
                        "Could not parse manifest `%s` in retarget_tag",
                        manifest_or_legacy_image._db_id,
                    )
                    return None

                if parsed.tag != tag_name:
                    logger.debug(
                        "Rewriting manifest `%s` for tag named `%s`",
                        manifest_or_legacy_image._db_id,
                        tag_name,
                    )

                    repository_id = repository_ref._db_id
                    updated = parsed.with_tag_name(tag_name, legacy_manifest_key)
                    assert updated.is_signed

                    created = oci.manifest.get_or_create_manifest(repository_id, updated, storage)
                    if created is None:
                        return None

                    manifest_id = created.manifest.id

        tag = oci.tag.retarget_tag(tag_name, manifest_id, is_reversion=is_reversion)
        legacy_image = LegacyImage.for_image(oci.shared.get_legacy_image_for_manifest(manifest_id))
        return Tag.for_tag(tag, legacy_image)

    def delete_tag(self, repository_ref, tag_name):
        """
        Deletes the latest, *active* tag with the given name in the repository.
        """
        deleted_tag = oci.tag.delete_tag(repository_ref._db_id, tag_name)
        if deleted_tag is None:
            # TODO: This is only needed because preoci raises an exception. Remove and fix
            # expected status codes once PreOCIModel is gone.
            msg = "Invalid repository tag '%s' on repository" % tag_name
            raise DataModelException(msg)

        return Tag.for_tag(deleted_tag)

    def delete_tags_for_manifest(self, manifest):
        """
        Deletes all tags pointing to the given manifest, making the manifest inaccessible for
        pulling.

        Returns the tags deleted, if any. Returns None on error.
        """
        deleted_tags = oci.tag.delete_tags_for_manifest(manifest._db_id)
        return [Tag.for_tag(tag) for tag in deleted_tags]

    def change_repository_tag_expiration(self, tag, expiration_date):
        """
        Sets the expiration date of the tag under the matching repository to that given.

        If the expiration date is None, then the tag will not expire. Returns a tuple of the
        previous expiration timestamp in seconds (if any), and whether the operation succeeded.
        """
        return oci.tag.change_tag_expiration(tag._db_id, expiration_date)

    def get_legacy_images_owned_by_tag(self, tag):
        """
        Returns all legacy images *solely owned and used* by the given tag.
        """
        tag_obj = oci.tag.get_tag_by_id(tag._db_id)
        if tag_obj is None:
            return None

        tags = oci.tag.list_alive_tags(tag_obj.repository_id)
        legacy_images = oci.tag.get_legacy_images_for_tags(tags)

        tag_legacy_image = legacy_images.get(tag._db_id)
        if tag_legacy_image is None:
            return None

        assert isinstance(tag_legacy_image, Image)

        # Collect the IDs of all images that the tag uses.
        tag_image_ids = set()
        tag_image_ids.add(tag_legacy_image.id)
        tag_image_ids.update(tag_legacy_image.ancestor_id_list())

        # Remove any images shared by other tags.
        for current in tags:
            if current == tag_obj:
                continue

            current_image = legacy_images.get(current.id)
            if current_image is None:
                continue

            tag_image_ids.discard(current_image.id)
            tag_image_ids = tag_image_ids.difference(current_image.ancestor_id_list())
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
            image = oci.shared.get_legacy_image_for_manifest(manifest_or_legacy_image._db_id)
            if image is None:
                return SecurityScanStatus.UNSUPPORTED
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
            image = oci.shared.get_legacy_image_for_manifest(manifest_or_legacy_image._db_id)
            if image is None:
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
        # Nothing to do for OCI tags.
        manifest = tag.manifest
        if manifest is None:
            return None

        legacy_image = oci.shared.get_legacy_image_for_manifest(manifest)
        return Manifest.for_manifest(manifest, LegacyImage.for_image(legacy_image))

    def list_manifest_layers(self, manifest, storage, include_placements=False):
        try:
            manifest_obj = database.Manifest.get(id=manifest._db_id)
        except database.Manifest.DoesNotExist:
            logger.exception("Could not find manifest for manifest `%s`", manifest._db_id)
            return None

        try:
            parsed = manifest.get_parsed_manifest()
        except ManifestException:
            logger.exception("Could not parse and validate manifest `%s`", manifest._db_id)
            return None

        return self._list_manifest_layers(
            manifest_obj.repository_id, parsed, storage, include_placements, by_manifest=True
        )

    def lookup_derived_image(
        self, manifest, verb, storage, varying_metadata=None, include_placements=False
    ):
        """
        Looks up the derived image for the given manifest, verb and optional varying metadata and
        returns it or None if none.
        """
        legacy_image = self._get_legacy_compatible_image_for_manifest(manifest, storage)
        if legacy_image is None:
            return None

        derived = model.image.find_derived_storage_for_image(legacy_image, verb, varying_metadata)
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
        legacy_image = self._get_legacy_compatible_image_for_manifest(manifest, storage)
        if legacy_image is None:
            return None

        derived = model.image.find_or_create_derived_storage(
            legacy_image, verb, storage_location, varying_metadata
        )
        return self._build_derived(derived, verb, varying_metadata, include_placements)

    def set_tags_expiration_for_manifest(self, manifest, expiration_sec):
        """
        Sets the expiration on all tags that point to the given manifest to that specified.
        """
        oci.tag.set_tag_expiration_sec_for_manifest(manifest._db_id, expiration_sec)

    def get_schema1_parsed_manifest(self, manifest, namespace_name, repo_name, tag_name, storage):
        """
        Returns the schema 1 manifest for this manifest, or None if none.
        """
        try:
            parsed = manifest.get_parsed_manifest()
        except ManifestException:
            return None

        try:
            manifest_row = database.Manifest.get(id=manifest._db_id)
        except database.Manifest.DoesNotExist:
            return None

        retriever = RepositoryContentRetriever(manifest_row.repository_id, storage)
        return parsed.get_schema1_manifest(namespace_name, repo_name, tag_name, retriever)

    def convert_manifest(
        self, manifest, namespace_name, repo_name, tag_name, allowed_mediatypes, storage
    ):
        try:
            parsed = manifest.get_parsed_manifest()
        except ManifestException:
            return None

        try:
            manifest_row = database.Manifest.get(id=manifest._db_id)
        except database.Manifest.DoesNotExist:
            return None

        retriever = RepositoryContentRetriever(manifest_row.repository_id, storage)
        return parsed.convert_manifest(
            allowed_mediatypes, namespace_name, repo_name, tag_name, retriever
        )

    def create_manifest_with_temp_tag(
        self, repository_ref, manifest_interface_instance, expiration_sec, storage
    ):
        """
        Creates a manifest under the repository and sets a temporary tag to point to it.

        Returns the manifest object created or None on error.
        """
        # Get or create the manifest itself. get_or_create_manifest will take care of the
        # temporary tag work.
        created_manifest = oci.manifest.get_or_create_manifest(
            repository_ref._db_id,
            manifest_interface_instance,
            storage,
            temp_tag_expiration_sec=expiration_sec,
        )
        if created_manifest is None:
            return None

        legacy_image = oci.shared.get_legacy_image_for_manifest(created_manifest.manifest)
        li = LegacyImage.for_image(legacy_image)
        return Manifest.for_manifest(created_manifest.manifest, li)

    def get_repo_blob_by_digest(self, repository_ref, blob_digest, include_placements=False):
        """
        Returns the blob in the repository with the given digest, if any or None if none.

        Note that there may be multiple records in the same repository for the same blob digest, so
        the return value of this function may change.
        """
        image_storage = self._get_shared_storage(blob_digest)
        if image_storage is None:
            image_storage = oci.blob.get_repository_blob_by_digest(
                repository_ref._db_id, blob_digest
            )
            if image_storage is None:
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
            repository_ref._db_id,
            parsed_manifest,
            storage,
            include_placements=include_placements,
            by_manifest=True,
        )

    def get_manifest_local_blobs(self, manifest, include_placements=False):
        """
        Returns the set of local blobs for the given manifest or None if none.
        """
        try:
            manifest_row = database.Manifest.get(id=manifest._db_id)
        except database.Manifest.DoesNotExist:
            return None

        return self._get_manifest_local_blobs(
            manifest, manifest_row.repository_id, include_placements, by_manifest=True
        )

    def yield_tags_for_vulnerability_notification(self, layer_id_pairs):
        """
        Yields tags that contain one (or more) of the given layer ID pairs, in repositories which
        have been registered for vulnerability_found notifications.

        Returns an iterator of LikelyVulnerableTag instances.
        """
        for docker_image_id, storage_uuid in layer_id_pairs:
            tags = oci.tag.lookup_notifiable_tags_for_legacy_image(
                docker_image_id, storage_uuid, "vulnerability_found"
            )
            for tag in tags:
                yield LikelyVulnerableTag.for_tag(
                    tag, tag.repository, docker_image_id, storage_uuid
                )


oci_model = OCIModel()
back_compat_oci_model = OCIModel(oci_model_only=False)
