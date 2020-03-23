import hashlib

import pytest

from data import model, database
from storage.basestorage import StoragePaths
from storage.fakestorage import FakeStorage
from storage.distributedstorage import DistributedStorage
from workers.storagereplication import (
    StorageReplicationWorker,
    JobException,
    WorkerUnhealthyException,
)

from test.fixtures import *


@pytest.fixture()
def storage_user(app):
    user = model.user.get_user("devtable")
    database.UserRegion.create(
        user=user, location=database.ImageStorageLocation.get(name="local_us")
    )
    database.UserRegion.create(
        user=user, location=database.ImageStorageLocation.get(name="local_eu")
    )
    return user


@pytest.fixture()
def storage_paths():
    return StoragePaths()


@pytest.fixture()
def replication_worker():
    return StorageReplicationWorker(None)


@pytest.fixture()
def storage():
    return DistributedStorage(
        {"local_us": FakeStorage("local"), "local_eu": FakeStorage("local")}, ["local_us"]
    )


def test_storage_replication_v1(storage_user, storage_paths, replication_worker, storage, app):
    # Add a storage entry with a V1 path.
    v1_storage = model.storage.create_v1_storage("local_us")
    content_path = storage_paths.v1_image_layer_path(v1_storage.uuid)
    storage.put_content(["local_us"], content_path, b"some content")

    # Call replicate on it and verify it replicates.
    replication_worker.replicate_storage(storage_user, v1_storage.uuid, storage)

    # Ensure that the data was replicated to the other "region".
    assert storage.get_content(["local_eu"], content_path) == b"some content"

    locations = model.storage.get_storage_locations(v1_storage.uuid)
    assert len(locations) == 2


def test_storage_replication_cas(storage_user, storage_paths, replication_worker, storage, app):
    # Add a storage entry with a CAS path.
    content_checksum = "sha256:" + hashlib.sha256(b"some content").hexdigest()
    cas_storage = database.ImageStorage.create(cas_path=True, content_checksum=content_checksum)

    location = database.ImageStorageLocation.get(name="local_us")
    database.ImageStoragePlacement.create(storage=cas_storage, location=location)

    content_path = storage_paths.blob_path(cas_storage.content_checksum)
    storage.put_content(["local_us"], content_path, b"some content")

    # Call replicate on it and verify it replicates.
    replication_worker.replicate_storage(storage_user, cas_storage.uuid, storage)

    # Ensure that the data was replicated to the other "region".
    assert storage.get_content(["local_eu"], content_path) == b"some content"

    locations = model.storage.get_storage_locations(cas_storage.uuid)
    assert len(locations) == 2


def test_storage_replication_missing_base(
    storage_user, storage_paths, replication_worker, storage, app
):
    # Add a storage entry with a CAS path.
    content_checksum = "sha256:" + hashlib.sha256(b"some content").hexdigest()
    cas_storage = database.ImageStorage.create(cas_path=True, content_checksum=content_checksum)

    location = database.ImageStorageLocation.get(name="local_us")
    database.ImageStoragePlacement.create(storage=cas_storage, location=location)

    # Attempt to replicate storage. This should fail because the layer is missing from the base
    # storage.
    with pytest.raises(JobException):
        replication_worker.replicate_storage(
            storage_user, cas_storage.uuid, storage, backoff_check=False
        )

    # Ensure the storage location count remains 1. This is technically inaccurate, but that's okay
    # as we still require at least one location per storage.
    locations = model.storage.get_storage_locations(cas_storage.uuid)
    assert len(locations) == 1


def test_storage_replication_copy_error(
    storage_user, storage_paths, replication_worker, storage, app
):
    # Add a storage entry with a CAS path.
    content_checksum = "sha256:" + hashlib.sha256(b"some content").hexdigest()
    cas_storage = database.ImageStorage.create(cas_path=True, content_checksum=content_checksum)

    location = database.ImageStorageLocation.get(name="local_us")
    database.ImageStoragePlacement.create(storage=cas_storage, location=location)

    content_path = storage_paths.blob_path(cas_storage.content_checksum)
    storage.put_content(["local_us"], content_path, b"some content")

    # Tell storage to break copying.
    storage.put_content(["local_us"], "break_copying", b"true")

    # Attempt to replicate storage. This should fail because the write fails.
    with pytest.raises(JobException):
        replication_worker.replicate_storage(
            storage_user, cas_storage.uuid, storage, backoff_check=False
        )

    # Ensure the storage location count remains 1.
    locations = model.storage.get_storage_locations(cas_storage.uuid)
    assert len(locations) == 1


def test_storage_replication_copy_didnot_copy(
    storage_user, storage_paths, replication_worker, storage, app
):
    # Add a storage entry with a CAS path.
    content_checksum = "sha256:" + hashlib.sha256(b"some content").hexdigest()
    cas_storage = database.ImageStorage.create(cas_path=True, content_checksum=content_checksum)

    location = database.ImageStorageLocation.get(name="local_us")
    database.ImageStoragePlacement.create(storage=cas_storage, location=location)

    content_path = storage_paths.blob_path(cas_storage.content_checksum)
    storage.put_content(["local_us"], content_path, b"some content")

    # Tell storage to fake copying (i.e. not actually copy the data).
    storage.put_content(["local_us"], "fake_copying", b"true")

    # Attempt to replicate storage. This should fail because the copy doesn't actually do the copy.
    with pytest.raises(JobException):
        replication_worker.replicate_storage(
            storage_user, cas_storage.uuid, storage, backoff_check=False
        )

    # Ensure the storage location count remains 1.
    locations = model.storage.get_storage_locations(cas_storage.uuid)
    assert len(locations) == 1


def test_storage_replication_copy_unhandled_exception(
    storage_user, storage_paths, replication_worker, storage, app
):
    # Add a storage entry with a CAS path.
    content_checksum = "sha256:" + hashlib.sha256(b"some content").hexdigest()
    cas_storage = database.ImageStorage.create(cas_path=True, content_checksum=content_checksum)

    location = database.ImageStorageLocation.get(name="local_us")
    database.ImageStoragePlacement.create(storage=cas_storage, location=location)

    content_path = storage_paths.blob_path(cas_storage.content_checksum)
    storage.put_content(["local_us"], content_path, b"some content")

    # Tell storage to raise an exception when copying.
    storage.put_content(["local_us"], "except_copying", b"true")

    # Attempt to replicate storage. This should fail because the copy raises an unhandled exception.
    with pytest.raises(WorkerUnhealthyException):
        replication_worker.replicate_storage(
            storage_user, cas_storage.uuid, storage, backoff_check=False
        )

    # Ensure the storage location count remains 1.
    locations = model.storage.get_storage_locations(cas_storage.uuid)
    assert len(locations) == 1
