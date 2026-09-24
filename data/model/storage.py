import logging
from collections import namedtuple
from contextvars import ContextVar

from cachetools.func import lru_cache
from peewee import SQL, IntegrityError

from data.database import (
    ImageStorage,
    ImageStorageLocation,
    ImageStoragePlacement,
    ImageStorageSignature,
    ImageStorageSignatureKind,
    ImageStorageTransformation,
    ManifestBlob,
    Namespace,
    Repository,
    UploadedBlob,
    ensure_under_transaction,
)
from data.model import (
    DataModelException,
    InvalidImageException,
    _basequery,
    config,
    db_transaction,
)
from util.locking import GlobalLock, LockAcquireTimeout, LockNotAcquiredException
from util.metrics.prometheus import gc_storage_blobs_deleted, gc_table_rows_deleted

logger = logging.getLogger(__name__)

_Location = namedtuple("_Location", ["id", "name"])

EMPTY_LAYER_BLOB_DIGEST = "sha256:a3ed95caeb02ffe68cdd9fd84406680ae93d633cb16422d00e8a7c22955b46d4"
SPECIAL_BLOB_DIGESTS = set([EMPTY_LAYER_BLOB_DIGEST])

# Total seconds a blob writer waits for a contended BLOB_DELETE lock before giving up.
BLOB_DELETE_LOCK_ACQUIRE_TIMEOUT = 3

# Why with_blob_lock_or_fallback is running func without the BLOB_DELETE lock (None while it holds
# the lock). func only receives skip_lock=True either way, so get_or_create_blob_with_lock reads
# this to decide whether it may create a missing blob.
_BLOB_LOCK_TIMED_OUT = "timed_out"
_BLOB_LOCK_UNAVAILABLE = "unavailable"
_blob_lock_fallback = ContextVar("blob_lock_fallback", default=None)


@lru_cache(maxsize=1)
def get_image_locations():
    location_map = {}
    for location in ImageStorageLocation.select():
        location_tuple = _Location(location.id, location.name)
        location_map[location.id] = location_tuple
        location_map[location.name] = location_tuple

    return location_map


def get_image_location_for_name(location_name):
    locations = get_image_locations()
    return locations[location_name]


def get_image_location_for_id(location_id):
    locations = get_image_locations()
    return locations[location_id]


def add_storage_placement(storage, location_name):
    """
    Adds a storage placement for the given storage at the given location.
    """
    location = get_image_location_for_name(location_name)
    try:
        ImageStoragePlacement.create(location=location.id, storage=storage)
    except IntegrityError:
        # Placement already exists. Nothing to do.
        pass


def _is_storage_orphaned(candidate_id):
    """
    Returns the whether the given candidate storage ID is orphaned. Must be executed
    under a transaction.
    """
    with ensure_under_transaction():
        try:
            ManifestBlob.get(blob=candidate_id)
            return False
        except ManifestBlob.DoesNotExist:
            pass

        try:
            UploadedBlob.get(blob=candidate_id)
            return False
        except UploadedBlob.DoesNotExist:
            pass

        # We need to check if a blob is a placeholder blob. If it is, we must **NOT** delete this blob.
        has_placement = (
            ImageStoragePlacement.select()
            .where(ImageStoragePlacement.storage == candidate_id)
            .exists()
        )

        if not has_placement:
            # Placeholder blobs will be GCed later in a future cycle or the download worker will download it
            logger.debug("Skipping GC of placeholder blob %s (no placement yet)", candidate_id)
            return False

    return True


def garbage_collect_storage(storage_id_whitelist, namespace=None, repo_name=None):
    """
    Performs GC on a possible subset of the storage's with the IDs found in the whitelist.

    The storages in the whitelist will be checked, and any orphaned will be removed, with those IDs
    being returned.
    """
    if len(storage_id_whitelist) == 0:
        return []

    def placements_to_filtered_paths_set(placements_list):
        """
        Returns the list of paths to remove from storage, filtered from the given placements query
        by removing any CAS paths that are still referenced by storage(s) in the database.
        """
        if not placements_list:
            return set()

        with ensure_under_transaction():
            # Find the content checksums not referenced by other storages. Any that are, we cannot
            # remove.
            content_checksums = set(
                [
                    placement.storage.content_checksum
                    for placement in placements_list
                    if placement.storage.cas_path
                ]
            )

            unreferenced_checksums = set()
            if content_checksums:
                # Check the current image storage.
                query = ImageStorage.select(ImageStorage.content_checksum).where(
                    ImageStorage.content_checksum << list(content_checksums)
                )
                is_referenced_checksums = set(
                    [image_storage.content_checksum for image_storage in query]
                )
                if is_referenced_checksums:
                    logger.warning(
                        "GC attempted to remove CAS checksums %s, which are still IS referenced",
                        is_referenced_checksums,
                    )

                unreferenced_checksums = content_checksums - is_referenced_checksums

            # Return all placements for all image storages found not at a CAS path or with a content
            # checksum that is referenced.
            return {
                (
                    get_image_location_for_id(placement.location_id).name,
                    get_layer_path(placement.storage),
                    placement.storage.content_checksum,
                )
                for placement in placements_list
                if not placement.storage.cas_path
                or placement.storage.content_checksum in unreferenced_checksums
            }

    # Note: Both of these deletes must occur in the same transaction (unfortunately) because a
    # storage without any placement is invalid, and a placement cannot exist without a storage.
    # TODO: We might want to allow for null storages on placements, which would allow us to
    # delete the storages, then delete the placements in a non-transaction.
    logger.debug("Garbage collecting storages from candidates: %s", storage_id_whitelist)
    paths_to_remove = []
    orphaned_storage_ids = set()
    for storage_id_to_check in storage_id_whitelist:
        logger.debug("Garbage collecting storage %s", storage_id_to_check)

        with db_transaction():
            if not _is_storage_orphaned(storage_id_to_check):
                continue

            orphaned_storage_ids.add(storage_id_to_check)

            placements_to_remove = list(
                ImageStoragePlacement.select(ImageStoragePlacement, ImageStorage)
                .join(ImageStorage)
                .where(ImageStorage.id == storage_id_to_check)
            )

            # Remove the placements for orphaned storages
            deleted_image_storage_placement = 0
            if placements_to_remove:
                deleted_image_storage_placement = (
                    ImageStoragePlacement.delete()
                    .where(ImageStoragePlacement.storage == storage_id_to_check)
                    .execute()
                )

            deleted_image_storage_signature = (
                ImageStorageSignature.delete()
                .where(ImageStorageSignature.storage == storage_id_to_check)
                .execute()
            )

            deleted_image_storage = (
                ImageStorage.delete().where(ImageStorage.id == storage_id_to_check).execute()
            )

            # Determine the paths to remove. We cannot simply remove all paths matching storages, as CAS
            # can share the same path. We further filter these paths by checking for any storages still in
            # the database with the same content checksum.
            paths_to_remove.extend(placements_to_filtered_paths_set(placements_to_remove))

        gc_table_rows_deleted.labels(table="ImageStorageSignature").inc(
            deleted_image_storage_signature
        )
        gc_table_rows_deleted.labels(table="ImageStorage").inc(deleted_image_storage)
        gc_table_rows_deleted.labels(table="ImageStoragePlacement").inc(
            deleted_image_storage_placement
        )

    # We are going to make the conscious decision to not delete image storage blobs inside
    # transactions.
    # This may end up producing garbage in s3, trading off for higher availability in the database.
    paths_to_remove = list(set(paths_to_remove))
    for location_name, image_path, storage_checksum in paths_to_remove:
        if storage_checksum:
            # Skip any specialized blob digests that we know we should keep around.
            if storage_checksum in SPECIAL_BLOB_DIGESTS:
                continue

            # Perform one final check to ensure the blob is not needed.
            # Note: GlobalLock ensures that deletion is atomic with the database operation, but does not
            # avoid *all* race conditions. However, it does make the window extremely small, potentially
            # happening only between the check and actual deletion under lock. Mitigations added in
            # _is_storage_orphaned and the UploadedBlob check should ensure further narrow the possible
            # race condition window.
            try:
                with GlobalLock(f"BLOB_DELETE_{storage_checksum}", lock_ttl=120):
                    if (
                        ImageStorage.select()
                        .where(ImageStorage.content_checksum == storage_checksum)
                        .exists()
                    ):
                        continue

                    version_id = config.store.remove({location_name}, image_path)
                    if namespace:
                        msg = "Removed blob %s from %s (path: %s) " "under namespace %s (repo: %s)"
                        args = [storage_checksum, location_name, image_path, namespace, repo_name]
                        if version_id:
                            msg += " (delete_marker: %s)"
                            args.append(version_id)
                        logger.info(msg, *args)
                    gc_storage_blobs_deleted.inc()
            # If a lock cannot be acquired, skip deletion of the blob from storage backend (safe option)
            except LockNotAcquiredException:
                logger.debug(
                    "Could not acquire lock for blob %s, skipping deletion", storage_checksum
                )
                continue
    return orphaned_storage_ids


def create_v1_storage(location_name):
    storage = ImageStorage.create(cas_path=False)
    location = get_image_location_for_name(location_name)
    ImageStoragePlacement.create(location=location.id, storage=storage)
    storage.locations = {location_name}
    return storage


def find_or_create_storage_signature(storage, signature_kind_name):
    found = lookup_storage_signature(storage, signature_kind_name)
    if found is None:
        kind = ImageStorageSignatureKind.get(name=signature_kind_name)
        found = ImageStorageSignature.create(storage=storage, kind=kind)

    return found


def lookup_storage_signature(storage, signature_kind_name):
    kind = ImageStorageSignatureKind.get(name=signature_kind_name)
    try:
        return (
            ImageStorageSignature.select()
            .where(ImageStorageSignature.storage == storage, ImageStorageSignature.kind == kind)
            .get()
        )
    except ImageStorageSignature.DoesNotExist:
        return None


def _get_storage(query_modifier):
    query = (
        ImageStoragePlacement.select(ImageStoragePlacement, ImageStorage)
        .switch(ImageStoragePlacement)
        .join(ImageStorage)
    )

    placements = list(query_modifier(query))

    if not placements:
        raise InvalidImageException()

    found = placements[0].storage
    found.locations = {
        get_image_location_for_id(placement.location_id).name for placement in placements
    }
    return found


def with_blob_lock_or_fallback(digest, func, *args, **kwargs):
    """
    Execute a function under the BLOB_DELETE GlobalLock, or without a lock if it cannot be
    acquired within BLOB_DELETE_LOCK_ACQUIRE_TIMEOUT.

    This helper consolidates the common pattern of:
    1. Try to acquire GlobalLock for blob deletion coordination (outer lock), bounded by
       BLOB_DELETE_LOCK_ACQUIRE_TIMEOUT
    2. Execute func with skip_lock=True (caller holds, or has already given up on, the lock)

    The primary purpose is to coordinate with garbage collection (GC) to prevent the race condition
    where GC deletes a blob from object storage while another operation is creating database entries
    for that same blob.

    Args:
        digest: Blob digest for lock key (e.g., "sha256:abc123...")
        func: Callable to execute (must accept skip_lock kwarg)
        *args, **kwargs: Arguments to pass to func

    Returns:
        Result of func()

    Fallback behavior:
        func is still called with skip_lock=True, so it does not re-attempt the same
        BLOB_DELETE_<digest> lock.

        If another holder (e.g., GC) still has the lock after BLOB_DELETE_LOCK_ACQUIRE_TIMEOUT, func
        may use an existing blob, but a missing one is not created: LockAcquireTimeout is raised
        and the registry returns a 5xx that clients retry. GC could be removing that blob's object
        from storage right now.

        If Redis is unavailable, func may also create a missing blob without the lock. The race
        condition can *still* happen then, but the window is extremely narrow, and database
        uniqueness constraints provide the ultimate safety guarantee. This lockless creation is
        the same as the logic that existed before the race condition fix.

        The fallback state is communicated to func via a ContextVar, so it only applies to
        digests that func creates by calling get_or_create_blob_with_lock(skip_lock=True); a
        func that creates blobs some other way is not covered by this fallback behavior.
    """
    try:
        with GlobalLock(
            f"BLOB_DELETE_{digest}",
            lock_ttl=30,
            blocking_timeout=BLOB_DELETE_LOCK_ACQUIRE_TIMEOUT,
        ):
            return func(*args, skip_lock=True, **kwargs)
    except LockAcquireTimeout:
        fallback = _BLOB_LOCK_TIMED_OUT
    except LockNotAcquiredException as e:
        logger.warning("Could not acquire lock for blob %s: %s", digest, e)
        fallback = _BLOB_LOCK_UNAVAILABLE

    token = _blob_lock_fallback.set(fallback)
    try:
        return func(*args, skip_lock=True, **kwargs)
    finally:
        _blob_lock_fallback.reset(token)


def _get_or_create_blob_with_lock(digest, lock_acquired=True, may_create=True, **blob_attrs):
    """
    Gets or creates the ImageStorage reference for the provided blob digest. If the reference to the blob
    does not exists in storage, we attempt to create it. If during creation an integrity error is raised (meaning
    another worker has created the reference already), we return the found reference.
    """
    try:
        return ImageStorage.get(content_checksum=digest)
    except ImageStorage.DoesNotExist:
        if not may_create:
            raise LockAcquireTimeout(
                "BLOB_DELETE_%s is held elsewhere; not creating blob %s without it"
                % (digest, digest)
            )
        if not lock_acquired:
            logger.warning("Blob %s: proceeding without lock", digest)
        try:
            return ImageStorage.create(content_checksum=digest, **blob_attrs)
        except IntegrityError as e:
            logger.warning("Another worker already created blob %s: %s", digest, e)
            return ImageStorage.get(content_checksum=digest)


def get_or_create_blob_with_lock(digest, skip_lock=False, **blob_attrs):
    """
    Atomically gets or creates an ImageStorage blob, coordinating with GC deletion.

    This function uses the same GlobalLock as the GC blob deletion path to ensure
    mutual exclusion between blob creation and deletion, preventing the race condition
    where a blob could be deleted from storage while a database record is being created.

    Args:
        digest: The blob digest (e.g., "sha256:abc123...")
        skip_lock: If False (default), acquire a lock inside this function. If True, do not acquire
        the lock (the caller holds it or has already given up on it).
        **blob_attrs: Additional attributes to pass to ImageStorage.create() if creating

    Returns:
        ImageStorage object (either existing or newly created)
    """
    if skip_lock:
        fallback = _blob_lock_fallback.get()
        return _get_or_create_blob_with_lock(
            digest,
            lock_acquired=fallback is None,
            may_create=fallback != _BLOB_LOCK_TIMED_OUT,
            **blob_attrs,
        )
    if GlobalLock.lock_factory is None:
        # No locking configured, proceed without lock
        return _get_or_create_blob_with_lock(digest, lock_acquired=False, **blob_attrs)
    try:
        with GlobalLock(
            f"BLOB_DELETE_{digest}",
            lock_ttl=30,
            blocking_timeout=BLOB_DELETE_LOCK_ACQUIRE_TIMEOUT,
        ):
            # If multiple workers try to create a blob at the same time, we must ensure that blob creation doesn't
            # fail. Otherwise, push will fail.
            return _get_or_create_blob_with_lock(digest, lock_acquired=True, **blob_attrs)
    except LockNotAcquiredException:
        # If we cannot acquire a lock, check if we have the ImageStorage entries for the provided
        # digest. If that reading fails, then create new entries in the table anyway but report
        # the lock failure in the log. If multiple workers try to create a blob at the same time, we must ensure
        # that blob creation doesn't fail. Otherwise, push will fail.
        return _get_or_create_blob_with_lock(digest, lock_acquired=False, **blob_attrs)


def get_storage_by_uuid(storage_uuid):
    def filter_to_uuid(query):
        return query.where(ImageStorage.uuid == storage_uuid)

    try:
        return _get_storage(filter_to_uuid)
    except InvalidImageException:
        raise InvalidImageException("No storage found with uuid: %s", storage_uuid)


def get_layer_path(storage_record):
    """
    Returns the path in the storage engine to the layer data referenced by the storage row.
    """
    assert storage_record.cas_path is not None
    return get_layer_path_for_storage(
        storage_record.uuid, storage_record.cas_path, storage_record.content_checksum
    )


def get_layer_path_for_storage(storage_uuid, cas_path, content_checksum):
    """
    Returns the path in the storage engine to the layer data referenced by the storage information.
    """
    store = config.store
    if not cas_path:
        logger.debug("Serving layer from legacy v1 path for storage %s", storage_uuid)
        return store.v1_image_layer_path(storage_uuid)

    return store.blob_path(content_checksum)


def lookup_repo_storages_by_content_checksum(repo, checksums, with_uploads=False):
    """
    Looks up repository storages (without placements) matching the given repository and checksum.
    """
    checksums = list(set(checksums))
    if not checksums:
        return []

    # If the request is not with uploads, simply return the blobs found under the manifests
    # for the repository.
    if not with_uploads:
        return _lookup_repo_storages_by_content_checksum(repo, checksums, ManifestBlob)

    # Otherwise, first check the UploadedBlob table and, once done, then check the ManifestBlob
    # table.
    found_via_uploaded = list(
        _lookup_repo_storages_by_content_checksum(repo, checksums, UploadedBlob)
    )
    if len(found_via_uploaded) == len(checksums):
        return found_via_uploaded

    checksums_remaining = set(checksums) - {
        uploaded.content_checksum for uploaded in found_via_uploaded
    }
    found_via_manifest = list(
        _lookup_repo_storages_by_content_checksum(repo, checksums_remaining, ManifestBlob)
    )
    return found_via_uploaded + found_via_manifest


def _lookup_repo_storages_by_content_checksum(repo, checksums, model_class):
    assert checksums

    # There may be many duplicates of the checksums, so for performance reasons we are going
    # to use a union to select just one storage with each checksum
    queries = []

    for counter, checksum in enumerate(checksums):
        query_alias = "q{0}".format(counter)

        candidate_subq = (
            ImageStorage.select(
                ImageStorage.id,
                ImageStorage.content_checksum,
                ImageStorage.image_size,
                ImageStorage.uuid,
                ImageStorage.cas_path,
                ImageStorage.uncompressed_size,
            )
            .join(model_class)
            .where(model_class.repository == repo, ImageStorage.content_checksum == checksum)
            .limit(1)
            .alias(query_alias)
        )

        queries.append(ImageStorage.select(SQL("*")).from_(candidate_subq))

    assert queries

    # Prevent crash on gunicorn (PROJQUAY-7603)
    # If the number of queries is too large, the UNION query
    # generated crashes gunicorn, instead run each query
    # individually
    if len(queries) > 1000:
        result = [next(iter(q.execute()), None) for q in queries]
        return [r for r in result if r is not None]

    return _basequery.reduce_as_tree(queries)


def get_storage_locations(uuid):
    query = ImageStoragePlacement.select().join(ImageStorage).where(ImageStorage.uuid == uuid)

    return [get_image_location_for_id(placement.location_id).name for placement in query]


def ensure_image_locations(*names):
    with db_transaction():
        locations = ImageStorageLocation.select().where(ImageStorageLocation.name << names)

        insert_names = list(names)

        for location in locations:
            insert_names.remove(location.name)

        if not insert_names:
            return

        data = [{"name": name} for name in insert_names]
        ImageStorageLocation.insert_many(data).execute()
