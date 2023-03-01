from collections import namedtuple
import time
from typing import Dict, List

from data.model import db_transaction

from peewee import fn
from data.database import (
    ImageStorage,
    ManifestBlob,
    ManifestChild,
    NamespaceSize,
    Repository,
    RepositorySize,
    Tag,
    User,
)

get_epoch_timestamp_ms = lambda: int(time.time() * 1000)

ID = 0
IMAGE_SIZE = 1


# storage_sizes: [(id, image_size),...]
def add_blob_size(repository_id: int, manifest_id: int, storage_sizes):
    update_sizes(repository_id, manifest_id, storage_sizes, "add")


# storage_sizes: [(id, image_size),...]
def subtract_blob_size(repository_id: int, manifest_id: int, storage_sizes):
    update_sizes(repository_id, manifest_id, storage_sizes, "subtract")


def update_sizes(repository_id: int, manifest_id: int, storage_sizes, operation: str):
    namespace_id = get_namespace_id_from_repository(repository_id)

    # Addition - if the blob already referenced it's already been counted
    # Subtraction - should only happen on the deletion of the last blob, if another exists
    # don't subtract
    namespace_total = 0
    repository_total = 0
    for storage_size in storage_sizes:
        # To account for schema 1, which doesn't include the compressed_size field
        blob_size = storage_size[IMAGE_SIZE] if storage_size[IMAGE_SIZE] is not None else 0
        if not blob_exists_in_namespace(namespace_id, manifest_id, storage_size[ID]):
            namespace_total = namespace_total + blob_size

        if not blob_exists_in_repository(repository_id, manifest_id, storage_size[ID]):
            repository_total = repository_total + blob_size

    write_namespace_total(namespace_id, manifest_id, namespace_total, operation)
    write_repository_total(repository_id, manifest_id, repository_total, operation)


def blob_exists_in_namespace(namespace_id: int, manifest_id: int, blob_id: int):
    try:
        (
            ManifestBlob.select(ManifestBlob.id)
            .join(Repository, on=(ManifestBlob.repository == Repository.id))
            .where(
                Repository.namespace_user == namespace_id,
                ManifestBlob.blob == blob_id,
                ManifestBlob.manifest != manifest_id,
            )
            .get()
        )
        return True
    except ManifestBlob.DoesNotExist:
        return False


def blob_exists_in_repository(repository_id: int, manifest_id: int, blob_id: int):
    try:
        (
            ManifestBlob.select(ManifestBlob.id)
            .where(
                ManifestBlob.repository == repository_id,
                ManifestBlob.blob == blob_id,
                ManifestBlob.manifest != manifest_id,
            )
            .get()
        )
        return True
    except ManifestBlob.DoesNotExist:
        return False


def write_namespace_total(
    namespace_id: int, manifest_id: int, namespace_total: int, operation: str
):
    namespace_size = get_namespace_size(namespace_id)
    namespace_size_exists = namespace_size is not None

    # If backfill hasn't ran yet for this namespace don't do anything
    if namespace_size_exists and (
        namespace_size.backfill_start_ms is None
        or namespace_size.backfill_start_ms > get_epoch_timestamp_ms()
    ):
        return

    # If the namespacesize entry doesn't exist and this is the only manifest in the namespace
    # we can assume this is the first push to the namespace and there is no blobs to be
    # backfilled, so let the entry be created. Otherwise it still needs to be handled by the
    # backfill worker so let's exit
    params = {}
    if (
        operation == "add"
        and not namespace_size_exists
        and only_manifest_in_namespace(namespace_id, manifest_id)
    ):
        params["backfill_start_ms"] = 0
        params["backfill_complete"] = True
    elif operation == "add" and not namespace_size_exists:
        return

    increment_namespacesize(namespace_id, namespace_total, operation, namespace_size_exists, params)


def write_repository_total(
    repository_id: int, manifest_id: int, repository_total: int, operation: str
):
    repository_size = get_repository_size(repository_id)
    repository_size_exists = repository_size is not None

    # If backfill hasn't ran yet for this repository don't do anything
    if repository_size_exists and (
        repository_size.backfill_start_ms is None
        or repository_size.backfill_start_ms > get_epoch_timestamp_ms()
    ):
        return

    # If the repositorysize entry doesn't exist and this is the only manifest in the repository
    # we can assume this is the first push to the repository and there is no blobs to be
    # backfilled, so let the entry be created. Otherwise it still needs to be handled by the
    # backfill worker so let's exit
    params = {}
    if (
        operation == "add"
        and not repository_size_exists
        and only_manifest_in_repository(repository_id, manifest_id)
    ):
        params["backfill_start_ms"] = 0
        params["backfill_complete"] = True
    elif operation == "add" and not repository_size_exists:
        return

    increment_repositorysize(
        repository_id, repository_total, operation, repository_size_exists, params
    )


def get_namespace_id_from_repository(repository: int):
    try:
        repo = Repository.select(Repository.namespace_user).where(Repository.id == repository).get()
        return repo.namespace_user_id
    except Repository.DoesNotExist:
        # TODO: should not happen
        return None


def get_namespace_size(namespace_id: int):
    try:
        namespace_size = (
            NamespaceSize.select().where(NamespaceSize.namespace_user_id == namespace_id).get()
        )
        return namespace_size
    except NamespaceSize.DoesNotExist:
        return None


def increment_namespacesize(
    namespace_id: int, size: int, operation: str, exists: bool, params=None
):
    params = params if params is not None else {}

    if exists:
        if operation == "add":
            params["size_bytes"] = NamespaceSize.size_bytes + size
        elif operation == "subtract":
            params["size_bytes"] = NamespaceSize.size_bytes - size
        NamespaceSize.update(**params).where(
            NamespaceSize.namespace_user_id == namespace_id
        ).execute()
    else:
        params["size_bytes"] = size
        # pylint: disable-next=no-value-for-parameter
        NamespaceSize.insert(namespace_user_id=namespace_id, **params).execute()


def get_repository_size(repository_id: int):
    try:
        repository_size = (
            RepositorySize.select().where(RepositorySize.repository_id == repository_id).get()
        )
        return repository_size
    except RepositorySize.DoesNotExist:
        return None


def increment_repositorysize(
    repository_id: int, size: int, operation: str, exists: bool, params=None
):
    params = params if params is not None else {}

    if exists:
        if operation == "add":
            params["size_bytes"] = RepositorySize.size_bytes + size
        elif operation == "subtract":
            params["size_bytes"] = RepositorySize.size_bytes - size
        RepositorySize.update(**params).where(RepositorySize.repository == repository_id).execute()
    else:
        params["size_bytes"] = size
        # pylint: disable-next=no-value-for-parameter
        RepositorySize.insert(repository_id=repository_id, **params).execute()


def only_manifest_in_namespace(namespace_id: int, manifest_id: int):
    try:
        (
            ManifestBlob.select()
            .join(Repository, on=(Repository.id == ManifestBlob.repository))
            .where(Repository.namespace_user == namespace_id, ManifestBlob.manifest != manifest_id)
            .get()
        )
        return False
    except ManifestBlob.DoesNotExist:
        return True


def only_manifest_in_repository(repository_id: int, manifest_id: int):
    try:
        ManifestBlob.select().where(
            ManifestBlob.repository == repository_id, ManifestBlob.manifest != manifest_id
        ).get()
        return False
    except ManifestBlob.DoesNotExist:
        return True


# Backfill of existing manifests
def run_backfill(namespace_id: int):
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
        print("catdebug", "namespace", namespace_id, "backfill", params)
        update_namespacesize(namespace_id, params, True)

    # pylint: disable-next=not-an-iterable
    for repository in repositories_in_namespace(namespace_id):
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
            print("catdebug", "repository", repository.id, "backfill", params)
            update_repositorysize(repository.id, params, True)


def get_namespace_total(namespace_id: int):
    derived_ns = (
        ImageStorage.select(ImageStorage.image_size)
        .join(ManifestBlob, on=(ImageStorage.id == ManifestBlob.blob))
        .join(Repository, on=(Repository.id == ManifestBlob.repository))
        .where(Repository.namespace_user == namespace_id)
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
    return Repository.select().where(Repository.namespace_user == namespace_id)


def update_namespacesize(namespace_id: int, params, exists=False):
    if exists:
        NamespaceSize.update(**params).where(
            NamespaceSize.namespace_user_id == namespace_id
        ).execute()
    else:
        # pylint: disable-next=no-value-for-parameter
        NamespaceSize.insert(namespace_user_id=namespace_id, **params).execute()


def update_repositorysize(repository_id: int, params, exists: bool):
    if exists:
        RepositorySize.update(**params).where(RepositorySize.repository == repository_id).execute()
    else:
        # pylint: disable-next=no-value-for-parameter
        RepositorySize.insert(repository_id=repository_id, **params).execute()


def reset_backfill(repository_id: int):
    try:
        RepositorySize.update({"backfill_start_ms": None, "backfill_complete": False}).where(
            RepositorySize.repository == repository_id
        ).execute()
        namespace_id = get_namespace_id_from_repository(repository_id)
        reset_namespace_backfill(namespace_id)
    except RepositorySize.DoesNotExist:
        pass


def reset_namespace_backfill(namespace_id: int):
    try:
        NamespaceSize.update({"backfill_start_ms": None, "backfill_complete": False}).where(
            NamespaceSize.namespace_user_id == namespace_id
        ).execute()
    except NamespaceSize.DoesNotExist:
        pass
