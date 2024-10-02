import logging
from datetime import datetime

from peewee import IntegrityError, fn

import features
from data.database import (
    AccessToken,
    ApprTag,
    BlobUpload,
    DeletedRepository,
    ImageStorage,
    Label,
    Manifest,
    ManifestBlob,
    ManifestChild,
    ManifestLabel,
    ManifestSecurityStatus,
    QuotaRepositorySize,
    RepoMirrorConfig,
    Repository,
    RepositoryActionCount,
    RepositoryAuthorizedEmail,
    RepositoryAutoPrunePolicy,
    RepositoryBuild,
    RepositoryBuildTrigger,
    RepositoryNotification,
    RepositoryPermission,
    RepositoryState,
    Star,
    Tag,
    UploadedBlob,
    db_for_update,
)
from data.model import _basequery, blob, config, db_transaction, storage
from data.model.notification import delete_tag_notifications_for_tag
from data.model.oci import tag as oci_tag
from data.model.quota import QuotaOperation, update_quota
from data.secscan_model import secscan_model
from util.metrics.prometheus import gc_repos_purged, gc_table_rows_deleted

logger = logging.getLogger(__name__)


class _GarbageCollectorContext(object):
    def __init__(self, repository):
        self.repository = repository
        self.manifest_ids = set()
        self.label_ids = set()
        self.blob_ids = set()

    def add_manifest_id(self, manifest_id):
        self.manifest_ids.add(manifest_id)

    def add_label_id(self, label_id):
        self.label_ids.add(label_id)

    def add_blob_id(self, blob_id):
        self.blob_ids.add(blob_id)

    def mark_label_id_removed(self, label_id):
        self.label_ids.remove(label_id)

    def mark_manifest_removed(self, manifest):
        self.manifest_ids.remove(manifest.id)

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
    assert Manifest.select().where(Manifest.repository == repo).count() == 0
    assert ManifestBlob.select().where(ManifestBlob.repository == repo).count() == 0
    assert UploadedBlob.select().where(UploadedBlob.repository == repo).count() == 0
    assert (
        ManifestSecurityStatus.select().where(ManifestSecurityStatus.repository == repo).count()
        == 0
    )
    # Delete auto-prune policy associated with the repository
    RepositoryAutoPrunePolicy.delete().where(RepositoryAutoPrunePolicy.repository == repo).execute()

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
    """Deletes all rows referencing the given repository in the given model."""
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

            _run_garbage_collection(context)

        if not found:
            break

    QuotaRepositorySize.delete().where(QuotaRepositorySize.repository == repo).execute()

    assert QuotaRepositorySize.select().where(QuotaRepositorySize.repository == repo).count() == 0
    assert Tag.select().where(Tag.repository == repo).count() == 0
    assert Manifest.select().where(Manifest.repository == repo).count() == 0
    assert ManifestBlob.select().where(ManifestBlob.repository == repo).count() == 0
    assert UploadedBlob.select().where(UploadedBlob.repository == repo).count() == 0


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

        # Delete the tag.
        delete_tag_notifications_for_tag(tag)
        tag.delete_instance()

    gc_table_rows_deleted.labels(table="Tag").inc()


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

        Referrer = Manifest.alias()
        # Check if the manifest is the subject of another manifest.
        # Note: Manifest referrers with a valid subject field are created a non expiring
        # hidden tag, in order to prevent GC from inadvertently removing a referrer.
        try:
            Manifest.select().join(Referrer, on=(Manifest.digest == Referrer.subject)).where(
                Manifest.id == manifest_id
            ).get()
            return True
        except Manifest.DoesNotExist:
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

        blob_sizes = {}
        if features.QUOTA_MANAGEMENT:
            # Get the blobs before they're deleted
            for manifest_blob in (
                ImageStorage.select(ImageStorage.image_size, ImageStorage.id)
                .join(ManifestBlob, on=(ImageStorage.id == ManifestBlob.blob))
                .where(
                    ManifestBlob.manifest == manifest_id,
                    ManifestBlob.repository == context.repository,
                )
            ):
                blob_sizes[manifest_blob.id] = manifest_blob.image_size

        # Delete the manifest blobs for the manifest.
        deleted_manifest_blob = (
            ManifestBlob.delete()
            .where(
                ManifestBlob.manifest == manifest_id, ManifestBlob.repository == context.repository
            )
            .execute()
        )

        # Subtract blob sizes if quota management is enabled
        update_quota(manifest.repository_id, manifest_id, blob_sizes, QuotaOperation.SUBTRACT)

        # Delete the security status for the manifest
        deleted_manifest_security = (
            ManifestSecurityStatus.delete()
            .where(
                ManifestSecurityStatus.manifest == manifest_id,
                ManifestSecurityStatus.repository == context.repository,
            )
            .execute()
        )

        # Delete the manifest.
        manifest.delete_instance()

    context.mark_manifest_removed(manifest)

    if features.SECURITY_SCANNER and config.app_config.get("SECURITY_SCANNER_V4_MANIFEST_CLEANUP"):
        try:
            secscan_model.garbage_collect_manifest_report(manifest.digest)
        except:
            logger.warning(
                "Exception attempting to delete manifest %s from secscan service" % manifest.digest
            )

    gc_table_rows_deleted.labels(table="ManifestLabel").inc(deleted_manifest_label)
    gc_table_rows_deleted.labels(table="ManifestChild").inc(deleted_manifest_child)
    gc_table_rows_deleted.labels(table="ManifestBlob").inc(deleted_manifest_blob)
    gc_table_rows_deleted.labels(table="ManifestSecurityStatus").inc(deleted_manifest_security)
    gc_table_rows_deleted.labels(table="Manifest").inc()

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
