import logging

from peewee import fn, IntegrityError
from datetime import datetime

from data.model import config, db_transaction, storage, _basequery, tag as pre_oci_tag, blob
from data.model.oci import tag as oci_tag
from data.database import Repository, db_for_update
from data.database import ApprTag
from data.database import (
    Tag,
    Manifest,
    DeletedRepository,
    ManifestBlob,
    ManifestChild,
    ManifestLegacyImage,
    ManifestLabel,
    ManifestSecurityStatus,
    Label,
    TagManifestLabel,
    RepositoryState,
    RepositoryBuild,
    RepositoryBuildTrigger,
    RepositoryActionCount,
    Star,
    AccessToken,
    RepositoryNotification,
    BlobUpload,
    RepoMirrorConfig,
    RepositoryPermission,
    RepositoryAuthorizedEmail,
    UploadedBlob,
)
from data.database import (
    RepositoryTag,
    TagManifest,
    Image,
    DerivedStorageForImage,
)
from data.database import TagManifestToManifest, TagToRepositoryTag, TagManifestLabelMap
from util.metrics.prometheus import gc_table_rows_deleted, gc_repos_purged


logger = logging.getLogger(__name__)


class _GarbageCollectorContext(object):
    def __init__(self, repository):
        self.repository = repository
        self.manifest_ids = set()
        self.label_ids = set()
        self.blob_ids = set()
        self.legacy_image_ids = set()

    def add_manifest_id(self, manifest_id):
        self.manifest_ids.add(manifest_id)

    def add_label_id(self, label_id):
        self.label_ids.add(label_id)

    def add_blob_id(self, blob_id):
        self.blob_ids.add(blob_id)

    def add_legacy_image_id(self, legacy_image_id):
        self.legacy_image_ids.add(legacy_image_id)

    def mark_label_id_removed(self, label_id):
        self.label_ids.remove(label_id)

    def mark_manifest_removed(self, manifest):
        self.manifest_ids.remove(manifest.id)

    def mark_legacy_image_removed(self, legacy_image):
        self.legacy_image_ids.remove(legacy_image.id)

    def mark_blob_id_removed(self, blob_id):
        self.blob_ids.remove(blob_id)


def purge_repository(repo, force=False):
    """
    Completely delete all traces of the repository.

    Will return True upon complete success, and False upon partial or total failure. Garbage
    collection is incremental and repeatable, so this return value does not need to be checked or
    responded to.
    """
    assert repo.state == RepositoryState.MARKED_FOR_DELETION or force

    # Update the repo state to ensure nothing else is written to it.
    repo.state = RepositoryState.MARKED_FOR_DELETION
    repo.save()

    # Delete the repository of all Appr-referenced entries.
    # Note that new-model Tag's must be deleted in *two* passes, as they can reference parent tags,
    # and MySQL is... particular... about such relationships when deleting.
    if repo.kind.name == "application":
        fst_pass = (
            ApprTag.delete()
            .where(ApprTag.repository == repo, ~(ApprTag.linked_tag >> None))
            .execute()
        )
        snd_pass = ApprTag.delete().where(ApprTag.repository == repo).execute()
        gc_table_rows_deleted.labels(table="ApprTag").inc(fst_pass + snd_pass)
    else:
        # GC to remove the images and storage.
        _purge_repository_contents(repo)

    # Ensure there are no additional tags, manifests, images or blobs in the repository.
    assert ApprTag.select().where(ApprTag.repository == repo).count() == 0
    assert Tag.select().where(Tag.repository == repo).count() == 0
    assert RepositoryTag.select().where(RepositoryTag.repository == repo).count() == 0
    assert Manifest.select().where(Manifest.repository == repo).count() == 0
    assert ManifestBlob.select().where(ManifestBlob.repository == repo).count() == 0
    assert UploadedBlob.select().where(UploadedBlob.repository == repo).count() == 0
    assert (
        ManifestSecurityStatus.select().where(ManifestSecurityStatus.repository == repo).count()
        == 0
    )
    assert Image.select().where(Image.repository == repo).count() == 0

    # Delete any repository build triggers, builds, and any other large-ish reference tables for
    # the repository.
    _chunk_delete_all(repo, RepositoryPermission, force=force)
    _chunk_delete_all(repo, RepositoryBuild, force=force)
    _chunk_delete_all(repo, RepositoryBuildTrigger, force=force)
    _chunk_delete_all(repo, RepositoryActionCount, force=force)
    _chunk_delete_all(repo, Star, force=force)
    _chunk_delete_all(repo, AccessToken, force=force)
    _chunk_delete_all(repo, RepositoryNotification, force=force)
    _chunk_delete_all(repo, BlobUpload, force=force)
    _chunk_delete_all(repo, RepoMirrorConfig, force=force)
    _chunk_delete_all(repo, RepositoryAuthorizedEmail, force=force)

    # Delete any marker rows for the repository.
    DeletedRepository.delete().where(DeletedRepository.repository == repo).execute()

    # Delete the rest of the repository metadata.
    try:
        # Make sure the repository still exists.
        fetched = Repository.get(id=repo.id)
    except Repository.DoesNotExist:
        return False

    try:
        fetched.delete_instance(recursive=True, delete_nullable=False, force=force)
        gc_repos_purged.inc()
        return True
    except IntegrityError:
        return False


def _chunk_delete_all(repo, model, force=False, chunk_size=500):
    """ Deletes all rows referencing the given repository in the given model. """
    assert repo.state == RepositoryState.MARKED_FOR_DELETION or force

    while True:
        min_id = model.select(fn.Min(model.id)).where(model.repository == repo).scalar()
        if min_id is None:
            return

        max_id = (
            model.select(fn.Max(model.id))
            .where(model.repository == repo, model.id <= (min_id + chunk_size))
            .scalar()
        )
        if min_id is None or max_id is None or min_id > max_id:
            return

        model.delete().where(
            model.repository == repo, model.id >= min_id, model.id <= max_id
        ).execute()


def _chunk_iterate_for_deletion(query, chunk_size=10):
    """
    Returns an iterator that loads the rows returned by the given query in chunks.

    Note that order is not guaranteed here, so this will only work (i.e. not return duplicates) if
    the rows returned are being deleted between calls.
    """
    while True:
        results = list(query.limit(chunk_size))
        if not results:
            return

        yield results


def _purge_repository_contents(repo):
    """
    Purges all the contents of a repository, removing all of its tags, manifests and images.
    """
    logger.debug("Purging repository %s", repo)

    # Purge via all the tags.
    while True:
        found = False
        for tags in _chunk_iterate_for_deletion(Tag.select().where(Tag.repository == repo)):
            logger.debug("Found %s tags to GC under repository %s", len(tags), repo)
            found = True
            context = _GarbageCollectorContext(repo)
            for tag in tags:
                logger.debug("Deleting tag %s under repository %s", tag, repo)
                assert tag.repository_id == repo.id
                _purge_oci_tag(tag, context, allow_non_expired=True)

            _run_garbage_collection(context)

        if not found:
            break

    # Purge any uploaded blobs that have expired.
    while True:
        found = False
        for uploaded_blobs in _chunk_iterate_for_deletion(
            UploadedBlob.select().where(UploadedBlob.repository == repo)
        ):
            logger.debug(
                "Found %s uploaded blobs to GC under repository %s", len(uploaded_blobs), repo
            )
            found = True
            context = _GarbageCollectorContext(repo)
            for uploaded_blob in uploaded_blobs:
                logger.debug("Deleting uploaded blob %s under repository %s", uploaded_blob, repo)
                assert uploaded_blob.repository_id == repo.id
                _purge_uploaded_blob(uploaded_blob, context, allow_non_expired=True)

        if not found:
            break

    # TODO: remove this once we've removed the foreign key constraints from RepositoryTag
    # and Image.
    while True:
        found = False
        repo_tag_query = RepositoryTag.select().where(RepositoryTag.repository == repo)
        for tags in _chunk_iterate_for_deletion(repo_tag_query):
            logger.debug("Found %s tags to GC under repository %s", len(tags), repo)
            found = True
            context = _GarbageCollectorContext(repo)

            for tag in tags:
                logger.debug("Deleting tag %s under repository %s", tag, repo)
                assert tag.repository_id == repo.id
                _purge_pre_oci_tag(tag, context, allow_non_expired=True)

            _run_garbage_collection(context)

        if not found:
            break

    assert Tag.select().where(Tag.repository == repo).count() == 0
    assert RepositoryTag.select().where(RepositoryTag.repository == repo).count() == 0
    assert Manifest.select().where(Manifest.repository == repo).count() == 0
    assert ManifestBlob.select().where(ManifestBlob.repository == repo).count() == 0
    assert UploadedBlob.select().where(UploadedBlob.repository == repo).count() == 0

    # Add all remaining images to a new context. We do this here to minimize the number of images
    # we need to load.
    while True:
        found_image = False
        image_context = _GarbageCollectorContext(repo)

        existing_count = Image.select().where(Image.repository == repo).count()
        if not existing_count:
            break

        for image in Image.select().where(Image.repository == repo):
            found_image = True
            logger.debug("Trying to delete image %s under repository %s", image, repo)
            assert image.repository_id == repo.id
            image_context.add_legacy_image_id(image.id)

        _run_garbage_collection(image_context)
        new_count = Image.select().where(Image.repository == repo).count()
        if new_count >= existing_count:
            raise Exception("GC purge bug! Please report this to support!")


def garbage_collect_repo(repo):
    """
    Performs garbage collection over the contents of a repository.
    """
    # Purge expired tags.
    had_changes = False

    for tags in _chunk_iterate_for_deletion(oci_tag.lookup_unrecoverable_tags(repo)):
        logger.debug("Found %s tags to GC under repository %s", len(tags), repo)
        context = _GarbageCollectorContext(repo)
        for tag in tags:
            logger.debug("Deleting tag %s under repository %s", tag, repo)
            assert tag.repository_id == repo.id
            assert tag.lifetime_end_ms is not None
            _purge_oci_tag(tag, context)

        _run_garbage_collection(context)
        had_changes = True

    # TODO: Remove once we've removed the foreign key constraints from RepositoryTag and Image.
    for tags in _chunk_iterate_for_deletion(pre_oci_tag.lookup_unrecoverable_tags(repo)):
        logger.debug("Found %s tags to GC under repository %s", len(tags), repo)
        context = _GarbageCollectorContext(repo)
        for tag in tags:
            logger.debug("Deleting tag %s under repository %s", tag, repo)
            assert tag.repository_id == repo.id
            assert tag.lifetime_end_ts is not None
            _purge_pre_oci_tag(tag, context)

        _run_garbage_collection(context)
        had_changes = True

    # Purge expired uploaded blobs.
    for uploaded_blobs in _chunk_iterate_for_deletion(blob.lookup_expired_uploaded_blobs(repo)):
        logger.debug("Found %s uploaded blobs to GC under repository %s", len(uploaded_blobs), repo)
        context = _GarbageCollectorContext(repo)
        for uploaded_blob in uploaded_blobs:
            logger.debug("Deleting uploaded blob %s under repository %s", uploaded_blob, repo)
            assert uploaded_blob.repository_id == repo.id
            _purge_uploaded_blob(uploaded_blob, context)

        _run_garbage_collection(context)
        had_changes = True

    return had_changes


def _run_garbage_collection(context):
    """
    Runs the garbage collection loop, deleting manifests, images, labels and blobs in an iterative
    fashion.
    """
    has_changes = True

    while has_changes:
        has_changes = False

        # GC all manifests encountered.
        for manifest_id in list(context.manifest_ids):
            if _garbage_collect_manifest(manifest_id, context):
                has_changes = True

        # GC all images encountered.
        for image_id in list(context.legacy_image_ids):
            if _garbage_collect_legacy_image(image_id, context):
                has_changes = True

        # GC all labels encountered.
        for label_id in list(context.label_ids):
            if _garbage_collect_label(label_id, context):
                has_changes = True

        # GC any blobs encountered.
        if context.blob_ids:
            storage_ids_removed = set(storage.garbage_collect_storage(context.blob_ids))
            for blob_removed_id in storage_ids_removed:
                context.mark_blob_id_removed(blob_removed_id)
                has_changes = True


def _purge_oci_tag(tag, context, allow_non_expired=False):
    assert tag.repository_id == context.repository.id

    if not allow_non_expired:
        assert tag.lifetime_end_ms is not None
        assert tag.lifetime_end_ms <= oci_tag.get_epoch_timestamp_ms()

    # Add the manifest to be GCed.
    context.add_manifest_id(tag.manifest_id)

    with db_transaction():
        # Reload the tag and verify its lifetime_end_ms has not changed.
        try:
            reloaded_tag = db_for_update(Tag.select().where(Tag.id == tag.id)).get()
        except Tag.DoesNotExist:
            return False

        assert reloaded_tag.id == tag.id
        assert reloaded_tag.repository_id == context.repository.id
        if reloaded_tag.lifetime_end_ms != tag.lifetime_end_ms:
            return False

        # Delete mapping rows.
        deleted_tag_to_repotag = (
            TagToRepositoryTag.delete().where(TagToRepositoryTag.tag == tag).execute()
        )

        # Delete the tag.
        tag.delete_instance()

    gc_table_rows_deleted.labels(table="Tag").inc()
    gc_table_rows_deleted.labels(table="TagToRepositoryTag").inc(deleted_tag_to_repotag)


def _purge_pre_oci_tag(tag, context, allow_non_expired=False):
    assert tag.repository_id == context.repository.id

    if not allow_non_expired:
        assert tag.lifetime_end_ts is not None
        assert tag.lifetime_end_ts <= pre_oci_tag.get_epoch_timestamp()

    # If it exists, GC the tag manifest.
    try:
        tag_manifest = TagManifest.select().where(TagManifest.tag == tag).get()
        _garbage_collect_legacy_manifest(tag_manifest.id, context)
    except TagManifest.DoesNotExist:
        pass

    # Add the tag's legacy image to be GCed.
    context.add_legacy_image_id(tag.image_id)

    with db_transaction():
        # Reload the tag and verify its lifetime_end_ts has not changed.
        try:
            reloaded_tag = db_for_update(
                RepositoryTag.select().where(RepositoryTag.id == tag.id)
            ).get()
        except RepositoryTag.DoesNotExist:
            return False

        assert reloaded_tag.id == tag.id
        assert reloaded_tag.repository_id == context.repository.id
        if reloaded_tag.lifetime_end_ts != tag.lifetime_end_ts:
            return False

        # Delete mapping rows.
        deleted_tag_to_repotag = (
            TagToRepositoryTag.delete()
            .where(TagToRepositoryTag.repository_tag == reloaded_tag)
            .execute()
        )

        # Delete the tag.
        reloaded_tag.delete_instance()

    gc_table_rows_deleted.labels(table="RepositoryTag").inc()
    gc_table_rows_deleted.labels(table="TagToRepositoryTag").inc(deleted_tag_to_repotag)


def _purge_uploaded_blob(uploaded_blob, context, allow_non_expired=False):
    assert allow_non_expired or uploaded_blob.expires_at <= datetime.utcnow()

    # Add the storage to be checked.
    context.add_blob_id(uploaded_blob.blob_id)

    # Delete the uploaded blob.
    uploaded_blob.delete_instance()
    gc_table_rows_deleted.labels(table="UploadedBlob").inc()


def _check_manifest_used(manifest_id):
    assert manifest_id is not None

    with db_transaction():
        # Check if the manifest is referenced by any other tag.
        try:
            Tag.select().where(Tag.manifest == manifest_id).get()
            return True
        except Tag.DoesNotExist:
            pass

        # Check if the manifest is referenced as a child of another manifest.
        try:
            ManifestChild.select().where(ManifestChild.child_manifest == manifest_id).get()
            return True
        except ManifestChild.DoesNotExist:
            pass

    return False


def _garbage_collect_manifest(manifest_id, context):
    assert manifest_id is not None

    # Make sure the manifest isn't referenced.
    if _check_manifest_used(manifest_id):
        return False

    # Add the manifest's blobs to the context to be GCed.
    for manifest_blob in ManifestBlob.select().where(ManifestBlob.manifest == manifest_id):
        context.add_blob_id(manifest_blob.blob_id)

    # Retrieve the manifest's associated image, if any.
    try:
        legacy_image_id = ManifestLegacyImage.get(manifest=manifest_id).image_id
        context.add_legacy_image_id(legacy_image_id)
    except ManifestLegacyImage.DoesNotExist:
        legacy_image_id = None

    # Add child manifests to be GCed.
    for connector in ManifestChild.select().where(ManifestChild.manifest == manifest_id):
        context.add_manifest_id(connector.child_manifest_id)

    # Add the labels to be GCed.
    for manifest_label in ManifestLabel.select().where(ManifestLabel.manifest == manifest_id):
        context.add_label_id(manifest_label.label_id)

    # Delete the manifest.
    with db_transaction():
        try:
            manifest = Manifest.select().where(Manifest.id == manifest_id).get()
        except Manifest.DoesNotExist:
            return False

        assert manifest.id == manifest_id
        assert manifest.repository_id == context.repository.id
        if _check_manifest_used(manifest_id):
            return False

        # Delete any label mappings.
        deleted_tag_manifest_label_map = (
            TagManifestLabelMap.delete()
            .where(TagManifestLabelMap.manifest == manifest_id)
            .execute()
        )

        # Delete any mapping rows for the manifest.
        deleted_tag_manifest_to_manifest = (
            TagManifestToManifest.delete()
            .where(TagManifestToManifest.manifest == manifest_id)
            .execute()
        )

        # Delete any label rows.
        deleted_manifest_label = (
            ManifestLabel.delete()
            .where(
                ManifestLabel.manifest == manifest_id,
                ManifestLabel.repository == context.repository,
            )
            .execute()
        )

        # Delete any child manifest rows.
        deleted_manifest_child = (
            ManifestChild.delete()
            .where(
                ManifestChild.manifest == manifest_id,
                ManifestChild.repository == context.repository,
            )
            .execute()
        )

        # Delete the manifest blobs for the manifest.
        deleted_manifest_blob = (
            ManifestBlob.delete()
            .where(
                ManifestBlob.manifest == manifest_id, ManifestBlob.repository == context.repository
            )
            .execute()
        )

        # Delete the security status for the manifest
        deleted_manifest_security = (
            ManifestSecurityStatus.delete()
            .where(
                ManifestSecurityStatus.manifest == manifest_id,
                ManifestSecurityStatus.repository == context.repository,
            )
            .execute()
        )

        # Delete the manifest legacy image row.
        deleted_manifest_legacy_image = 0
        if legacy_image_id:
            deleted_manifest_legacy_image = (
                ManifestLegacyImage.delete()
                .where(
                    ManifestLegacyImage.manifest == manifest_id,
                    ManifestLegacyImage.repository == context.repository,
                )
                .execute()
            )

        # Delete the manifest.
        manifest.delete_instance()

    context.mark_manifest_removed(manifest)

    gc_table_rows_deleted.labels(table="TagManifestLabelMap").inc(deleted_tag_manifest_label_map)
    gc_table_rows_deleted.labels(table="TagManifestToManifest").inc(
        deleted_tag_manifest_to_manifest
    )
    gc_table_rows_deleted.labels(table="ManifestLabel").inc(deleted_manifest_label)
    gc_table_rows_deleted.labels(table="ManifestChild").inc(deleted_manifest_child)
    gc_table_rows_deleted.labels(table="ManifestBlob").inc(deleted_manifest_blob)
    gc_table_rows_deleted.labels(table="ManifestSecurityStatus").inc(deleted_manifest_security)
    if deleted_manifest_legacy_image:
        gc_table_rows_deleted.labels(table="ManifestLegacyImage").inc(deleted_manifest_legacy_image)

    gc_table_rows_deleted.labels(table="Manifest").inc()

    return True


def _garbage_collect_legacy_manifest(legacy_manifest_id, context):
    assert legacy_manifest_id is not None

    # Add the labels to be GCed.
    query = TagManifestLabel.select().where(TagManifestLabel.annotated == legacy_manifest_id)
    for manifest_label in query:
        context.add_label_id(manifest_label.label_id)

    # Delete the tag manifest.
    with db_transaction():
        try:
            tag_manifest = TagManifest.select().where(TagManifest.id == legacy_manifest_id).get()
        except TagManifest.DoesNotExist:
            return False

        assert tag_manifest.id == legacy_manifest_id
        assert tag_manifest.tag.repository_id == context.repository.id

        # Delete any label mapping rows.
        (
            TagManifestLabelMap.delete()
            .where(TagManifestLabelMap.tag_manifest == legacy_manifest_id)
            .execute()
        )

        # Delete the label rows.
        TagManifestLabel.delete().where(TagManifestLabel.annotated == legacy_manifest_id).execute()

        # Delete the mapping row if it exists.
        try:
            tmt = (
                TagManifestToManifest.select()
                .where(TagManifestToManifest.tag_manifest == tag_manifest)
                .get()
            )
            context.add_manifest_id(tmt.manifest_id)
            tmt_deleted = tmt.delete_instance()
            if tmt_deleted:
                gc_table_rows_deleted.labels(table="TagManifestToManifest").inc()
        except TagManifestToManifest.DoesNotExist:
            pass

        # Delete the tag manifest.
        tag_manifest_deleted = tag_manifest.delete_instance()
        if tag_manifest_deleted:
            gc_table_rows_deleted.labels(table="TagManifest").inc()
    return True


def _check_image_used(legacy_image_id):
    assert legacy_image_id is not None

    with db_transaction():
        # Check if the image is referenced by a manifest.
        try:
            ManifestLegacyImage.select().where(ManifestLegacyImage.image == legacy_image_id).get()
            return True
        except ManifestLegacyImage.DoesNotExist:
            pass

        # Check if the image is referenced by a tag.
        try:
            RepositoryTag.select().where(RepositoryTag.image == legacy_image_id).get()
            return True
        except RepositoryTag.DoesNotExist:
            pass

        # Check if the image is referenced by another image.
        try:
            Image.select().where(Image.parent == legacy_image_id).get()
            return True
        except Image.DoesNotExist:
            pass

    return False


def _garbage_collect_legacy_image(legacy_image_id, context):
    assert legacy_image_id is not None

    # Check if the image is referenced.
    if _check_image_used(legacy_image_id):
        return False

    # We have an unreferenced image. We can now delete it.
    # Grab any derived storage for the image.
    for derived in DerivedStorageForImage.select().where(
        DerivedStorageForImage.source_image == legacy_image_id
    ):
        context.add_blob_id(derived.derivative_id)

    try:
        image = Image.select().where(Image.id == legacy_image_id).get()
    except Image.DoesNotExist:
        return False

    assert image.repository_id == context.repository.id

    # Add the image's blob to be GCed.
    context.add_blob_id(image.storage_id)

    # If the image has a parent ID, add the parent for GC.
    if image.parent_id is not None:
        context.add_legacy_image_id(image.parent_id)

    # Delete the image.
    with db_transaction():
        if _check_image_used(legacy_image_id):
            return False

        try:
            image = Image.select().where(Image.id == legacy_image_id).get()
        except Image.DoesNotExist:
            return False

        assert image.id == legacy_image_id
        assert image.repository_id == context.repository.id

        # Delete any derived storage for the image.
        deleted_derived_storage = (
            DerivedStorageForImage.delete()
            .where(DerivedStorageForImage.source_image == legacy_image_id)
            .execute()
        )

        # Delete the image itself.
        image.delete_instance()

    context.mark_legacy_image_removed(image)

    gc_table_rows_deleted.labels(table="Image").inc()
    gc_table_rows_deleted.labels(table="DerivedStorageForImage").inc(deleted_derived_storage)

    if config.image_cleanup_callbacks:
        for callback in config.image_cleanup_callbacks:
            callback([image])

    return True


def _check_label_used(label_id):
    assert label_id is not None

    with db_transaction():
        # Check if the label is referenced by another manifest or tag manifest.
        try:
            ManifestLabel.select().where(ManifestLabel.label == label_id).get()
            return True
        except ManifestLabel.DoesNotExist:
            pass

        try:
            TagManifestLabel.select().where(TagManifestLabel.label == label_id).get()
            return True
        except TagManifestLabel.DoesNotExist:
            pass

    return False


def _garbage_collect_label(label_id, context):
    assert label_id is not None

    # We can now delete the label.
    with db_transaction():
        if _check_label_used(label_id):
            return False

        result = Label.delete().where(Label.id == label_id).execute() == 1

    if result:
        context.mark_label_id_removed(label_id)
        gc_table_rows_deleted.labels(table="Label").inc(result)

    return result
