import logging
import time
from collections import namedtuple
from typing import Dict, List

from peewee import JOIN, fn

from data.database import (
    ImageStorage,
    ManifestBlob,
    ManifestChild,
    QuotaNamespaceSize,
    QuotaRegistrySize,
    QuotaRepositorySize,
    Repository,
    RepositoryState,
    Tag,
    User,
)
from data.model import config, db_transaction
from data.model.repository import lookup_repository

logger = logging.getLogger(__name__)

get_epoch_timestamp_ms = lambda: int(time.time() * 1000)


def add_blob_size(repository_id: int, manifest_id: int, blobs: dict):
    update_sizes(repository_id, manifest_id, blobs, "add")


def subtract_blob_size(repository_id: int, manifest_id: int, blobs: dict):
    update_sizes(repository_id, manifest_id, blobs, "subtract")


def update_sizes(repository_id: int, manifest_id: int, blobs: dict, operation: str):
    """
    Adds or subtracts the blobs that are currently not being referrenced by
    existing manifests from the total
    """
    if len(blobs) == 0:
        return

    namespace_id = get_namespace_id_from_repository(repository_id)
    if not eligible_namespace(namespace_id):
        return

    # Addition - if the blob already referenced it's already been counted
    # Subtraction - should only happen on the deletion of the last blob, if another exists
    # don't subtract
    namespace_total = 0
    repository_total = 0
    for blob_id, blob_image_size in blobs.items():

        # If the blob doesn't exist in the namespace it doesn't exist in the repo either
        # so add the total to both. If it exists in the namespace we need to check
        # if it exists in the repository.
        blob_size = blob_image_size if blob_image_size is not None else 0
        if not blob_exists_in_namespace(namespace_id, manifest_id, blob_id):
            namespace_total = namespace_total + blob_size
            repository_total = repository_total + blob_size
        elif not blob_exists_in_repository(repository_id, manifest_id, blob_id):
            repository_total = repository_total + blob_size

    write_namespace_total(namespace_id, manifest_id, namespace_total, operation)

    # TODO: If repository is marked for deletion or doesn't exist, don't write total
    write_repository_total(repository_id, manifest_id, repository_total, operation)


def blob_exists_in_namespace(namespace_id: int, manifest_id: int, blob_id: int):
    # Return true if there exists some other manifest within the namespace that
    # references this blob
    return (
        ManifestBlob.select(1)
        .join(Repository, on=(ManifestBlob.repository == Repository.id))
        .where(
            Repository.namespace_user == namespace_id,
            ManifestBlob.blob == blob_id,
            ManifestBlob.manifest != manifest_id,
        )
        .exists()
    )


def blob_exists_in_repository(repository_id: int, manifest_id: int, blob_id: int):
    # Return true if there exists some other manifest within the repository that
    # references this blob
    return (
        ManifestBlob.select(1)
        .where(
            ManifestBlob.repository == repository_id,
            ManifestBlob.blob == blob_id,
            ManifestBlob.manifest != manifest_id,
        )
        .exists()
    )


def write_namespace_total(
    namespace_id: int, manifest_id: int, namespace_total: int, operation: str
):
    namespace_size = get_namespace_size(namespace_id)
    namespace_size_exists = namespace_size is not None

    # TODO: The following checks should be before the blob lookup to prevent
    # unnecessary reads

    # If backfill hasn't ran yet for this namespace don't do anything
    if namespace_size_exists and not namespace_size.backfill_complete:
        return

    # If the namespacesize entry doesn't exist and this is the only manifest in the namespace
    # we can assume this is the first push to the namespace and there is no blobs to be
    # backfilled, so let the entry be created. Otherwise it still needs to be handled by the
    # backfill worker so let's exit
    if (
        operation == "add"
        and not namespace_size_exists
        and only_manifest_in_namespace(namespace_id, manifest_id)
    ):
        # pylint: disable-next=no-value-for-parameter
        QuotaNamespaceSize.insert(
            namespace_user_id=namespace_id,
            backfill_start_ms=0,
            backfill_complete=True,
            size_bytes=namespace_total,
        ).execute()
        return

    # If the quotanamespacesize entry doesn't exist and it's not the only
    # manifest in the repository, it needs to be handled by the backfill worker.
    # If it does exist we can add/subtract the total
    if namespace_size_exists:
        params = {}
        if operation == "add":
            params["size_bytes"] = QuotaNamespaceSize.size_bytes + namespace_total
        elif operation == "subtract":
            params["size_bytes"] = QuotaNamespaceSize.size_bytes - namespace_total
        QuotaNamespaceSize.update(**params).where(
            QuotaNamespaceSize.namespace_user == namespace_id
        ).execute()


def write_repository_total(
    repository_id: int, manifest_id: int, repository_total: int, operation: str
):
    repository_size = get_repository_size(repository_id)
    repository_size_exists = repository_size is not None

    # TODO: The following checks should be before the blob lookup to prevent
    # unnecessary reads

    # If backfill hasn't ran yet for this repository don't do anything
    if repository_size_exists and not repository_size.backfill_complete:
        return

    # If the repositorysize entry doesn't exist and this is the only manifest in the repository
    # we can assume this is the first push to the repository and there is no blobs to be
    # backfilled, so let the entry be created. Otherwise it still needs to be handled by the
    # backfill worker so let's exit
    if (
        operation == "add"
        and not repository_size_exists
        and only_manifest_in_repository(repository_id, manifest_id)
    ):
        # pylint: disable-next=no-value-for-parameter
        QuotaRepositorySize.insert(
            repository_id=repository_id,
            backfill_start_ms=0,
            backfill_complete=True,
            size_bytes=repository_total,
        ).execute()
        return

    # If the quotarepositorysize entry doesn't exist and it's not the only
    # manifest in the repository, it needs to be handled by the backfill worker.
    # If it does exist we can add/subtract the total
    if repository_size_exists:
        params = {}
        if operation == "add":
            params["size_bytes"] = QuotaRepositorySize.size_bytes + repository_total
        elif operation == "subtract":
            params["size_bytes"] = QuotaRepositorySize.size_bytes - repository_total
        QuotaRepositorySize.update(**params).where(
            QuotaRepositorySize.repository == repository_id
        ).execute()


def get_namespace_id_from_repository(repository: int):
    try:
        repo = Repository.select(Repository.namespace_user).where(Repository.id == repository).get()
        return repo.namespace_user_id
    except Repository.DoesNotExist:
        return None


def get_namespace_size(namespace_id: int):
    try:
        namespace_size = (
            QuotaNamespaceSize.select()
            .where(QuotaNamespaceSize.namespace_user == namespace_id)
            .get()
        )
        return namespace_size
    except QuotaNamespaceSize.DoesNotExist:
        return None


def get_repository_size(repository_id: int):
    try:
        repository_size = (
            QuotaRepositorySize.select()
            .where(QuotaRepositorySize.repository == repository_id)
            .get()
        )
        return repository_size
    except QuotaRepositorySize.DoesNotExist:
        return None


def only_manifest_in_namespace(namespace_id: int, manifest_id: int):
    return not (
        ManifestBlob.select(1)
        .join(Repository, on=(Repository.id == ManifestBlob.repository))
        .where(
            Repository.namespace_user == namespace_id,
            ManifestBlob.manifest != manifest_id,
            Repository.state != RepositoryState.MARKED_FOR_DELETION,
        )
        .exists()
    )


def only_manifest_in_repository(repository_id: int, manifest_id: int):
    return not (
        ManifestBlob.select(1)
        .where(ManifestBlob.repository == repository_id, ManifestBlob.manifest != manifest_id)
        .exists()
    )


def is_blob_alive(namespace_id: int, tag_id: int, blob_id: int):
    # Check if the blob is being referenced by an alive, non-hidden tag that isn't the
    # tag we're currently creating/deleting within the namespace.
    # Since sub-manifests are only considered alive if their parent tag is alive,
    # check the parent tag as well.
    # The where statements create an if ... else ... statement creating the logic:
    # if ParentTag is None:
    #     check that Tag is not hidden, alive, and in the namespace
    # elif ParentTag is not None:
    #     check that ParentTag is not hidden, alive, and in the namespace
    ParentTag = Tag.alias()
    return (
        ManifestBlob.select(1)
        .join(Repository, on=(ManifestBlob.repository == Repository.id))
        .join(Tag, on=(Tag.manifest == ManifestBlob.manifest))
        .join(
            ManifestChild,
            on=(ManifestBlob.manifest == ManifestChild.child_manifest),
            join_type=JOIN.LEFT_OUTER,
        )
        .join(
            ParentTag, on=(ManifestChild.manifest == ParentTag.manifest), join_type=JOIN.LEFT_OUTER
        )
        .where(
            (
                ParentTag.id.is_null(True)
                & ~Tag.hidden
                & (Repository.namespace_user == namespace_id)
                & (ManifestBlob.blob == blob_id)
                & (Tag.id != tag_id)
                & (
                    Tag.lifetime_end_ms.is_null(True)
                    | (Tag.lifetime_end_ms > get_epoch_timestamp_ms())
                )
            )
            | (
                ParentTag.id.is_null(False)
                & ~ParentTag.hidden
                & (Repository.namespace_user == namespace_id)
                & (ParentTag.id != tag_id)
                & (ManifestBlob.blob == blob_id)
                & (
                    ParentTag.lifetime_end_ms.is_null(True)
                    | (ParentTag.lifetime_end_ms > get_epoch_timestamp_ms())
                )
            )
        )
        .exists()
    )


def eligible_namespace(namespace_id):
    """
    Returns true if the namespace is eligible to have a quota size
    """
    return User.select(1).where(User.id == namespace_id, User.enabled, ~User.robot).exists()


def run_backfill(namespace_id: int):
    """
    Calculates the total of unique blobs in the namespace and repositories within
    the namespace.
    """
    namespace_size = get_namespace_size(namespace_id)
    namespace_size_exists = namespace_size is not None

    if not namespace_size_exists or (
        namespace_size_exists
        and not namespace_size.backfill_complete
        and namespace_size.backfill_start_ms is None
    ):
        params = {
            "size_bytes": 0,
            "backfill_start_ms": get_epoch_timestamp_ms(),
            "backfill_complete": False,
        }
        update_namespacesize(namespace_id, params, namespace_size_exists)

        params = {"size_bytes": get_namespace_total(namespace_id), "backfill_complete": True}
        update_namespacesize(namespace_id, params, True)

    # pylint: disable-next=not-an-iterable
    for repository in repositories_in_namespace(namespace_id):

        # Check to make sure the repository hasn't been deleted since the time passed
        latest_repository = lookup_repository(repository.id)
        if (
            latest_repository is None
            or latest_repository.state == RepositoryState.MARKED_FOR_DELETION
        ):
            return

        repository_size = get_repository_size(repository.id)
        repository_size_exists = repository_size is not None
        if not repository_size_exists or (
            repository_size_exists
            and not repository_size.backfill_complete
            and repository_size.backfill_start_ms is None
        ):
            params = {
                "size_bytes": 0,
                "backfill_start_ms": get_epoch_timestamp_ms(),
                "backfill_complete": False,
            }
            update_repositorysize(repository.id, params, repository_size_exists)

            params = {"size_bytes": get_repository_total(repository.id), "backfill_complete": True}
            update_repositorysize(repository.id, params, True)


def get_namespace_total(namespace_id: int):
    derived_ns = (
        ImageStorage.select(ImageStorage.image_size)
        .join(ManifestBlob, on=(ImageStorage.id == ManifestBlob.blob))
        .join(Repository, on=(Repository.id == ManifestBlob.repository))
        .where(
            Repository.namespace_user == namespace_id,
        )
        .group_by(ImageStorage.id)
    )
    total = ImageStorage.select(fn.Sum(derived_ns.c.image_size)).from_(derived_ns).scalar()
    return total if total is not None else 0


def get_repository_total(repository_id: int):
    derived_ns = (
        ImageStorage.select(ImageStorage.image_size)
        .join(ManifestBlob, on=(ImageStorage.id == ManifestBlob.blob))
        .where(ManifestBlob.repository == repository_id)
        .group_by(ImageStorage.id)
    )
    total = ImageStorage.select(fn.Sum(derived_ns.c.image_size)).from_(derived_ns).scalar()
    return total if total is not None else 0


def repositories_in_namespace(namespace_id: int):
    return Repository.select().where(
        Repository.namespace_user == namespace_id,
        Repository.state != RepositoryState.MARKED_FOR_DELETION,
    )


def update_namespacesize(namespace_id: int, params, exists=False):
    if exists:
        QuotaNamespaceSize.update(**params).where(
            QuotaNamespaceSize.namespace_user == namespace_id
        ).execute()
    else:
        # pylint: disable-next=no-value-for-parameter
        QuotaNamespaceSize.insert(namespace_user_id=namespace_id, **params).execute()


def update_repositorysize(repository_id: int, params, exists: bool):
    if exists:
        QuotaRepositorySize.update(**params).where(
            QuotaRepositorySize.repository == repository_id
        ).execute()
    else:
        # pylint: disable-next=no-value-for-parameter
        QuotaRepositorySize.insert(repository_id=repository_id, **params).execute()


def reset_backfill(repository_id: int):
    """
    Resets the quotarepositorysize fields to be picked up by the backfill worker
    for recalculation. Since the repository total will change we
    need to reset the namespace backfill has well.
    """
    if not config.app_config.get("QUOTA_INVALIDATE_TOTALS", True):
        return

    try:
        QuotaRepositorySize.update(
            {"size_bytes": 0, "backfill_start_ms": None, "backfill_complete": False}
        ).where(QuotaRepositorySize.repository == repository_id).execute()
        namespace_id = get_namespace_id_from_repository(repository_id)
        reset_namespace_backfill(namespace_id)
    except QuotaRepositorySize.DoesNotExist:
        pass


def reset_namespace_backfill(namespace_id: int):
    """
    Resets the quotanamespacesize fields to be picked up by the backfill worker
    for recalculation.
    """
    if not config.app_config.get("QUOTA_INVALIDATE_TOTALS", True):
        return

    try:
        QuotaNamespaceSize.update(
            {"size_bytes": 0, "backfill_start_ms": None, "backfill_complete": False}
        ).where(QuotaNamespaceSize.namespace_user == namespace_id).execute()
    except QuotaNamespaceSize.DoesNotExist:
        pass


def calculate_registry_size():
    """
    Calculates the size of the registry. Concurrency is done through the
    quotaregistrysize.running field.
    """
    quota_registry_size = get_registry_size()
    exists = quota_registry_size is not None

    if exists and not quota_registry_size.running and quota_registry_size.queued:
        set_registry_size_running(exists)
        logger.info("Calculating registry size")
        total_size = sum_registry_size()
        logger.info("Completed calculation of registry size")
        update_registry_size(total_size)


def get_registry_size():
    try:
        return QuotaRegistrySize.select().get()
    except QuotaRegistrySize.DoesNotExist:
        return None


def queue_registry_size_calculation():
    """
    Queues the registry size calculation for the quotaregistrysizeworker by
    setting quotaregistrysize.queued to true. Returns whether the calculation has been queued
    and whether it was already queued.
    """
    registry_size = get_registry_size()
    registry_size_exists = registry_size is not None

    if not registry_size_exists:
        # pylint: disable-next=no-value-for-parameter
        QuotaRegistrySize.insert(
            {"size_bytes": 0, "running": False, "queued": True, "completed_ms": None}
        ).execute()
        logger.info("Queued initial registry size calculation")
        return True, False

    if registry_size_exists and (registry_size.queued or registry_size.running):
        logger.info("Registry size calculation already queued")
        return True, True

    if registry_size_exists and (not registry_size.running and not registry_size.queued):
        # pylint: disable-next=no-value-for-parameter
        updated = QuotaRegistrySize.update({"queued": True}).execute()
        if updated != 0:
            logger.info("Queued registry size calculation")
        return updated != 0, False


def set_registry_size_running(exists=False):
    if exists:
        # pylint: disable-next=no-value-for-parameter
        QuotaRegistrySize.update({"running": True, "queued": False}).execute()
    else:
        # pylint: disable-next=no-value-for-parameter
        QuotaRegistrySize.insert({"running": True, "queued": False}).execute()


def sum_registry_size():
    # pylint: disable-next=no-value-for-parameter
    total_size = ImageStorage.select(fn.SUM(ImageStorage.image_size)).scalar()
    return total_size if total_size is not None else 0


def update_registry_size(size=0):
    # pylint: disable-next=no-value-for-parameter
    QuotaRegistrySize.update(
        {
            "running": False,
            "queued": False,
            "size_bytes": size,
            "completed_ms": get_epoch_timestamp_ms(),
        }
    ).execute()
