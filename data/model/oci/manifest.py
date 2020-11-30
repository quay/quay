import json
import logging
import os

from collections import namedtuple

from peewee import IntegrityError

from data.database import (
    Tag,
    Manifest,
    ManifestBlob,
    ManifestLegacyImage,
    ManifestChild,
    ImageStorage,
    ImageStoragePlacement,
    ImageStorageTransformation,
    ImageStorageSignature,
    Repository,
    RepositoryNotification,
    ExternalNotificationEvent,
    db_transaction,
)
from data.model import BlobDoesNotExist
from data.model.blob import get_or_create_shared_blob, get_shared_blob
from data.model.oci.tag import filter_to_alive_tags, create_temporary_tag_if_necessary
from data.model.oci.label import create_manifest_label
from data.model.oci.retriever import RepositoryContentRetriever
from data.model.storage import lookup_repo_storages_by_content_checksum, create_v1_storage
from data.model.image import lookup_repository_images, get_image, synthesize_v1_image
from image.docker.schema2 import EMPTY_LAYER_BLOB_DIGEST, EMPTY_LAYER_BYTES
from image.docker.schema1 import ManifestException
from image.docker.schema2.list import MalformedSchema2ManifestList
from util.canonicaljson import canonicalize
from util.validation import is_json


TEMP_TAG_EXPIRATION_SEC = 300  # 5 minutes


logger = logging.getLogger(__name__)

CreatedManifest = namedtuple("CreatedManifest", ["manifest", "newly_created", "labels_to_apply"])


class CreateManifestException(Exception):
    """
    Exception raised when creating a manifest fails and explicit exception raising is requested.
    """


class _ManifestAlreadyExists(Exception):
    """
    Exception raised to break out of manifest creation due to the manifest already existing.
    """

    def __init__(self, internal_exception):
        self.internal_exception = internal_exception


def find_manifests_for_sec_notification(manifest_digest):
    """
    Finds all manifests matching the given digest that live in a repository with a registered
    notification event for security scan results.
    """

    return (
        Manifest.select(Manifest, Repository)
        .join(Repository)
        .join(RepositoryNotification)
        .where(
            Manifest.digest == manifest_digest,
            RepositoryNotification.event
            == ExternalNotificationEvent.get(name="vulnerability_found"),
        )
    )


def lookup_manifest(
    repository_id,
    manifest_digest,
    allow_dead=False,
    require_available=False,
    temp_tag_expiration_sec=TEMP_TAG_EXPIRATION_SEC,
):
    """
    Returns the manifest with the specified digest under the specified repository or None if none.

    If allow_dead is True, then manifests referenced by only dead tags will also be returned. If
    require_available is True, the manifest will be marked with a temporary tag to ensure it remains
    available.
    """
    if not require_available:
        return _lookup_manifest(repository_id, manifest_digest, allow_dead=allow_dead)

    with db_transaction():
        found = _lookup_manifest(repository_id, manifest_digest, allow_dead=allow_dead)
        if found is None:
            return None

        create_temporary_tag_if_necessary(found, temp_tag_expiration_sec)
        return found


def _lookup_manifest(repository_id, manifest_digest, allow_dead=False):
    query = (
        Manifest.select()
        .where(Manifest.repository == repository_id)
        .where(Manifest.digest == manifest_digest)
    )

    if allow_dead:
        try:
            return query.get()
        except Manifest.DoesNotExist:
            return None

    # Try first to filter to those manifests referenced by an alive tag,
    try:
        return filter_to_alive_tags(query.join(Tag)).get()
    except Manifest.DoesNotExist:
        pass

    # Try referenced as the child of a manifest that has an alive tag.
    query = query.join(ManifestChild, on=(ManifestChild.child_manifest == Manifest.id)).join(
        Tag, on=(Tag.manifest == ManifestChild.manifest)
    )

    query = filter_to_alive_tags(query)

    try:
        return query.get()
    except Manifest.DoesNotExist:
        return None


def get_or_create_manifest(
    repository_id,
    manifest_interface_instance,
    storage,
    temp_tag_expiration_sec=TEMP_TAG_EXPIRATION_SEC,
    for_tagging=False,
    raise_on_error=False,
    retriever=None,
):
    """
    Returns a CreatedManifest for the manifest in the specified repository with the matching digest
    (if it already exists) or, if not yet created, creates and returns the manifest.

    Returns None if there was an error creating the manifest, unless raise_on_error is specified,
    in which case a CreateManifestException exception will be raised instead to provide more
    context to the error.

    Note that *all* blobs referenced by the manifest must exist already in the repository or this
    method will fail with a None.
    """
    existing = lookup_manifest(
        repository_id,
        manifest_interface_instance.digest,
        allow_dead=True,
        require_available=True,
        temp_tag_expiration_sec=temp_tag_expiration_sec,
    )
    if existing is not None:
        return CreatedManifest(manifest=existing, newly_created=False, labels_to_apply=None)

    return _create_manifest(
        repository_id,
        manifest_interface_instance,
        storage,
        temp_tag_expiration_sec,
        for_tagging=for_tagging,
        raise_on_error=raise_on_error,
        retriever=retriever,
    )


def _create_manifest(
    repository_id,
    manifest_interface_instance,
    storage,
    temp_tag_expiration_sec=TEMP_TAG_EXPIRATION_SEC,
    for_tagging=False,
    raise_on_error=False,
    retriever=None,
):
    # Validate the manifest.
    retriever = retriever or RepositoryContentRetriever.for_repository(repository_id, storage)
    try:
        manifest_interface_instance.validate(retriever)
    except (ManifestException, MalformedSchema2ManifestList, BlobDoesNotExist, IOError) as ex:
        logger.exception("Could not validate manifest `%s`", manifest_interface_instance.digest)
        if raise_on_error:
            raise CreateManifestException(str(ex))

        return None

    # Load, parse and get/create the child manifests, if any.
    child_manifest_refs = manifest_interface_instance.child_manifests(retriever)
    child_manifest_rows = {}
    child_manifest_label_dicts = []

    if child_manifest_refs is not None:
        for child_manifest_ref in child_manifest_refs:
            # Load and parse the child manifest.
            try:
                child_manifest = child_manifest_ref.manifest_obj
            except (
                ManifestException,
                MalformedSchema2ManifestList,
                BlobDoesNotExist,
                IOError,
            ) as ex:
                logger.exception(
                    "Could not load manifest list for manifest `%s`",
                    manifest_interface_instance.digest,
                )
                if raise_on_error:
                    raise CreateManifestException(str(ex))

                return None

            # Retrieve its labels.
            labels = child_manifest.get_manifest_labels(retriever)
            if labels is None:
                if raise_on_error:
                    raise CreateManifestException("Unable to retrieve manifest labels")

                logger.exception("Could not load manifest labels for child manifest")
                return None

            # Get/create the child manifest in the database.
            child_manifest_info = get_or_create_manifest(
                repository_id, child_manifest, storage, raise_on_error=raise_on_error
            )
            if child_manifest_info is None:
                if raise_on_error:
                    raise CreateManifestException("Unable to retrieve child manifest")

                logger.error("Could not get/create child manifest")
                return None

            child_manifest_rows[child_manifest_info.manifest.digest] = child_manifest_info.manifest
            child_manifest_label_dicts.append(labels)

    # Build the map from required blob digests to the blob objects.
    blob_map = _build_blob_map(
        repository_id,
        manifest_interface_instance,
        retriever,
        storage,
        raise_on_error,
        require_empty_layer=False,
    )
    if blob_map is None:
        return None

    # Create the manifest and its blobs.
    media_type = Manifest.media_type.get_id(manifest_interface_instance.media_type)
    storage_ids = {storage.id for storage in list(blob_map.values())}

    # Check for the manifest, in case it was created since we checked earlier.
    try:
        manifest = Manifest.get(repository=repository_id, digest=manifest_interface_instance.digest)
        return CreatedManifest(manifest=manifest, newly_created=False, labels_to_apply=None)
    except Manifest.DoesNotExist:
        pass

    try:
        with db_transaction():
            # Create the manifest.
            try:
                manifest = Manifest.create(
                    repository=repository_id,
                    digest=manifest_interface_instance.digest,
                    media_type=media_type,
                    manifest_bytes=manifest_interface_instance.bytes.as_encoded_str(),
                    config_media_type=manifest_interface_instance.config_media_type,
                    layers_compressed_size=manifest_interface_instance.layers_compressed_size,
                )
            except IntegrityError as ie:
                # NOTE: An IntegrityError means (barring a bug) that the manifest was created by
                # another caller while we were attempting to create it. Since we need to return
                # the manifest, we raise a specialized exception here to break out of the
                # transaction so we can retrieve it.
                raise _ManifestAlreadyExists(ie)

            # Insert the blobs.
            blobs_to_insert = [
                dict(manifest=manifest, repository=repository_id, blob=storage_id)
                for storage_id in storage_ids
            ]
            if blobs_to_insert:
                try:
                    ManifestBlob.insert_many(blobs_to_insert).execute()
                except IntegrityError as ie:
                    raise _ManifestAlreadyExists(ie)

            # Insert the manifest child rows (if applicable).
            if child_manifest_rows:
                children_to_insert = [
                    dict(manifest=manifest, child_manifest=child_manifest, repository=repository_id)
                    for child_manifest in list(child_manifest_rows.values())
                ]
                try:
                    ManifestChild.insert_many(children_to_insert).execute()
                except IntegrityError as ie:
                    raise _ManifestAlreadyExists(ie)

            # If this manifest is being created not for immediate tagging, add a temporary tag to the
            # manifest to ensure it isn't being GCed. If the manifest *is* for tagging, then since we're
            # creating a new one here, it cannot be GCed (since it isn't referenced by anything yet), so
            # its safe to elide the temp tag operation. If we ever change GC code to collect *all* manifests
            # in a repository for GC, then we will have to reevaluate this optimization at that time.
            if not for_tagging:
                create_temporary_tag_if_necessary(manifest, temp_tag_expiration_sec)

        # Define the labels for the manifest (if any).
        # TODO: Once the old data model is gone, turn this into a batch operation and make the label
        # application to the manifest occur under the transaction.
        labels = manifest_interface_instance.get_manifest_labels(retriever)
        if labels:
            for key, value in labels.items():
                # NOTE: There can technically be empty label keys via Dockerfile's. We ignore any
                # such `labels`, as they don't really mean anything.
                if not key:
                    continue

                media_type = "application/json" if is_json(value) else "text/plain"
                create_manifest_label(manifest, key, value, "manifest", media_type)

        # Return the dictionary of labels to apply (i.e. those labels that cause an action to be taken
        # on the manifest or its resulting tags). We only return those labels either defined on
        # the manifest or shared amongst all the child manifests. We intersect amongst all child manifests
        # to ensure that any action performed is defined in all manifests.
        labels_to_apply = labels or {}
        if child_manifest_label_dicts:
            labels_to_apply = child_manifest_label_dicts[0].items()
            for child_manifest_label_dict in child_manifest_label_dicts[1:]:
                # Intersect the key+values of the labels to ensure we get the exact same result
                # for all the child manifests.
                labels_to_apply = labels_to_apply & child_manifest_label_dict.items()

            labels_to_apply = dict(labels_to_apply)

        return CreatedManifest(
            manifest=manifest, newly_created=True, labels_to_apply=labels_to_apply
        )
    except _ManifestAlreadyExists as mae:
        try:
            manifest = Manifest.get(
                repository=repository_id, digest=manifest_interface_instance.digest
            )
        except Manifest.DoesNotExist:
            # NOTE: If we've reached this point, then somehow we had an IntegrityError without it
            # being due to a duplicate manifest. We therefore log the error.
            logger.error(
                "Got integrity error when trying to create manifest: %s", mae.internal_exception
            )
            if raise_on_error:
                raise CreateManifestException(
                    "Attempt to create an invalid manifest. Please report this issue."
                )

            return None

        return CreatedManifest(manifest=manifest, newly_created=False, labels_to_apply=None)


def _build_blob_map(
    repository_id,
    manifest_interface_instance,
    retriever,
    storage,
    raise_on_error=False,
    require_empty_layer=True,
):
    """Builds a map containing the digest of each blob referenced by the given manifest,
    to its associated Blob row in the database. This method also verifies that the blob
    is accessible under the given repository. Returns None on error (unless raise_on_error
    is specified). If require_empty_layer is set to True, the method will check if the manifest
    references the special shared empty layer blob and, if so, add it to the map. Otherwise,
    the empty layer blob is only returned if it was *explicitly* referenced in the manifest.
    This is necessary because Docker V2_2/OCI manifests can implicitly reference an empty blob
    layer for image layers that only change metadata.
    """

    # Ensure all the blobs in the manifest exist.
    digests = set(manifest_interface_instance.local_blob_digests)
    blob_map = {}

    # If the special empty layer is required, simply load it directly. This is much faster
    # than trying to load it on a per repository basis, and that is unnecessary anyway since
    # this layer is predefined.
    if EMPTY_LAYER_BLOB_DIGEST in digests:
        digests.remove(EMPTY_LAYER_BLOB_DIGEST)
        blob_map[EMPTY_LAYER_BLOB_DIGEST] = get_shared_blob(EMPTY_LAYER_BLOB_DIGEST)
        if not blob_map[EMPTY_LAYER_BLOB_DIGEST]:
            if raise_on_error:
                raise CreateManifestException("Unable to retrieve specialized empty blob")

            logger.warning("Could not find the special empty blob in storage")
            return None

    if digests:
        query = lookup_repo_storages_by_content_checksum(repository_id, digests, with_uploads=True)
        blob_map.update({s.content_checksum: s for s in query})
        for digest_str in digests:
            if digest_str not in blob_map:
                logger.warning(
                    "Unknown blob `%s` under manifest `%s` for repository `%s`",
                    digest_str,
                    manifest_interface_instance.digest,
                    repository_id,
                )

                if raise_on_error:
                    raise CreateManifestException("Unknown blob `%s`" % digest_str)

                return None

    # Special check: If the empty layer blob is needed for this manifest, add it to the
    # blob map. This is necessary because Docker decided to elide sending of this special
    # empty layer in schema version 2, but we need to have it referenced for schema version 1.
    if require_empty_layer and EMPTY_LAYER_BLOB_DIGEST not in blob_map:
        try:
            requires_empty_layer = manifest_interface_instance.get_requires_empty_layer_blob(
                retriever
            )
        except ManifestException as ex:
            if raise_on_error:
                raise CreateManifestException(str(ex))

            return None

        if requires_empty_layer is None:
            if raise_on_error:
                raise CreateManifestException("Could not load configuration blob")

            return None

        if requires_empty_layer:
            shared_blob = get_or_create_shared_blob(
                EMPTY_LAYER_BLOB_DIGEST, EMPTY_LAYER_BYTES, storage
            )
            assert not shared_blob.uploading
            assert shared_blob.content_checksum == EMPTY_LAYER_BLOB_DIGEST
            blob_map[EMPTY_LAYER_BLOB_DIGEST] = shared_blob

    return blob_map


def populate_legacy_images_for_testing(manifest, manifest_interface_instance, storage):
    """ Populates the legacy image rows for the given manifest. """
    # NOTE: This method is only kept around for use by legacy tests that still require
    # legacy images. As a result, we make sure we're in testing mode before we run.
    assert os.getenv("TEST") == "true"

    repository_id = manifest.repository_id
    retriever = RepositoryContentRetriever.for_repository(repository_id, storage)

    blob_map = _build_blob_map(
        repository_id, manifest_interface_instance, storage, True, require_empty_layer=True
    )
    if blob_map is None:
        return None

    # Determine and populate the legacy image if necessary. Manifest lists will not have a legacy
    # image.
    legacy_image = None
    if manifest_interface_instance.has_legacy_image:
        try:
            legacy_image_id = _populate_legacy_image(
                repository_id, manifest_interface_instance, blob_map, retriever, True
            )
        except ManifestException as me:
            raise CreateManifestException(
                "Attempt to create an invalid manifest: %s. Please report this issue." % me
            )

        if legacy_image_id is None:
            return None

        legacy_image = get_image(repository_id, legacy_image_id)
        if legacy_image is None:
            return None

        # Set the legacy image (if applicable).
        if legacy_image is not None:
            ManifestLegacyImage.create(
                repository=repository_id, image=legacy_image, manifest=manifest
            )


def _populate_legacy_image(
    repository_id, manifest_interface_instance, blob_map, retriever, raise_on_error=False
):
    # Lookup all the images and their parent images (if any) inside the manifest.
    # This will let us know which v1 images we need to synthesize and which ones are invalid.
    docker_image_ids = list(manifest_interface_instance.get_legacy_image_ids(retriever))
    images_query = lookup_repository_images(repository_id, docker_image_ids)
    image_storage_map = {i.docker_image_id: i.storage for i in images_query}

    # Rewrite any v1 image IDs that do not match the checksum in the database.
    try:
        rewritten_images = manifest_interface_instance.generate_legacy_layers(
            image_storage_map, retriever
        )
        rewritten_images = list(rewritten_images)
        parent_image_map = {}

        for rewritten_image in rewritten_images:
            if not rewritten_image.image_id in image_storage_map:
                parent_image = None
                if rewritten_image.parent_image_id:
                    parent_image = parent_image_map.get(rewritten_image.parent_image_id)
                    if parent_image is None:
                        parent_image = get_image(repository_id, rewritten_image.parent_image_id)
                        if parent_image is None:
                            if raise_on_error:
                                raise CreateManifestException(
                                    "Missing referenced parent image %s"
                                    % rewritten_image.parent_image_id
                                )

                            return None

                storage_reference = blob_map[rewritten_image.content_checksum]
                synthesized = synthesize_v1_image(
                    repository_id,
                    storage_reference.id,
                    storage_reference.image_size,
                    rewritten_image.image_id,
                    rewritten_image.created,
                    rewritten_image.comment,
                    rewritten_image.command,
                    rewritten_image.compat_json,
                    parent_image,
                )

                parent_image_map[rewritten_image.image_id] = synthesized
    except ManifestException as me:
        logger.exception("exception when rewriting v1 metadata")
        if raise_on_error:
            raise CreateManifestException(me)

        return None

    assert rewritten_images
    return rewritten_images[-1].image_id
