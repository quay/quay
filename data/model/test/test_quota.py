import json
from test.fixtures import *
from unittest.mock import MagicMock, patch

import pytest

from app import storage
from data.database import ImageStorageLocation, QuotaRegistrySize, Tag
from data.model.blob import store_blob_record_and_temp_link
from data.model.gc import _garbage_collect_manifest, _GarbageCollectorContext
from data.model.namespacequota import get_namespace_size
from data.model.oci.manifest import get_or_create_manifest
from data.model.organization import create_organization
from data.model.quota import (
    calculate_registry_size,
    get_registry_size,
    queue_registry_size_calculation,
    run_backfill,
    sum_registry_size,
)
from data.model.repository import create_repository, get_repository_size
from data.model.storage import get_layer_path
from data.model.user import get_user
from digest.digest_tools import sha256_digest
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from util.bytes import Bytes

ORG_NAME = "org1"
REPO1_NAME = "repo1"
REPO2_NAME = "repo2"
BLOB1 = "blob1"
BLOB2 = "blob2"
BLOB3 = "blob3"
BLOB4 = "blob4"
BLOB5 = "blob5"
BLOB6 = "blob6"
BLOB7 = "blob7"
CONFIG_LAYER_JSON = json.dumps(
    {
        "config": {},
        "rootfs": {"type": "layers", "diff_ids": []},
        "history": [],
    }
)


class TestQuota:
    @pytest.fixture(autouse=True)
    def setup(self, initialized_db):
        user = get_user("devtable")
        self.org = create_organization(ORG_NAME, f"{ORG_NAME}@devtable.com", user)
        self.repo1 = create_repository(ORG_NAME, REPO1_NAME, user)
        self.repo1manifest1 = create_manifest_for_testing(self.repo1, [BLOB1, BLOB2])
        self.repo1manifest2 = create_manifest_for_testing(self.repo1, [BLOB1, BLOB3])
        self.repo2 = create_repository(ORG_NAME, REPO2_NAME, user)
        self.repo2manifest3 = create_manifest_for_testing(self.repo2, [BLOB1, BLOB4])

    def test_run_backfill(self, initialized_db):
        run_backfill(self.org.id)
        assert get_namespace_size(ORG_NAME) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(
            BLOB2
        ) + len(BLOB3) + len(BLOB4)
        assert get_repository_size(self.repo1) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(
            BLOB2
        ) + len(BLOB3)
        assert get_repository_size(self.repo2) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(BLOB4)

    def test_adding_blob(self, initialized_db):
        run_backfill(self.org.id)
        assert get_namespace_size(ORG_NAME) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(
            BLOB2
        ) + len(BLOB3) + len(BLOB4)
        assert get_repository_size(self.repo1) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(
            BLOB2
        ) + len(BLOB3)
        assert get_repository_size(self.repo2) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(BLOB4)

        with patch("data.model.oci.manifest.features", MagicMock()) as mock_features:
            mock_features.QUOTA_MANAGEMENT = True
            create_manifest_for_testing(self.repo1, [BLOB5])
            assert get_namespace_size(ORG_NAME) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(
                BLOB2
            ) + len(BLOB3) + len(BLOB4) + len(BLOB5)
            assert get_repository_size(self.repo1) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(
                BLOB2
            ) + len(BLOB3) + len(BLOB5)
            assert get_repository_size(self.repo2) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(
                BLOB4
            )

    def test_subtracting_blob(self, initialized_db):
        run_backfill(self.org.id)
        assert get_namespace_size(ORG_NAME) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(
            BLOB2
        ) + len(BLOB3) + len(BLOB4)
        assert get_repository_size(self.repo1) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(
            BLOB2
        ) + len(BLOB3)
        assert get_repository_size(self.repo2) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(BLOB4)
        with patch("data.model.gc.features", MagicMock()) as mock_features:
            mock_features.QUOTA_MANAGEMENT = True
            tag_deleted = _delete_tag_for_manifest(self.repo2manifest3.id)
            assert tag_deleted
            context = _GarbageCollectorContext(self.repo2)
            context.add_manifest_id(self.repo2manifest3.id)
            manifest_deleted = _garbage_collect_manifest(self.repo2manifest3.id, context)
            assert manifest_deleted
            assert get_namespace_size(ORG_NAME) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(
                BLOB2
            ) + len(BLOB3)
            assert get_repository_size(self.repo1) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(
                BLOB2
            ) + len(BLOB3)
            assert get_repository_size(self.repo2) == 0

    def test_disabled_namespace(self, initialized_db):
        run_backfill(self.org.id)
        assert get_namespace_size(ORG_NAME) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(
            BLOB2
        ) + len(BLOB3) + len(BLOB4)
        assert get_repository_size(self.repo1) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(
            BLOB2
        ) + len(BLOB3)
        assert get_repository_size(self.repo2) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(BLOB4)

        self.org.enabled = False
        self.org.save()

        with patch("data.model.oci.manifest.features", MagicMock()) as mock_features:
            mock_features.QUOTA_MANAGEMENT = True
            create_manifest_for_testing(self.repo1, [BLOB5])
            assert get_namespace_size(ORG_NAME) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(
                BLOB2
            ) + len(BLOB3) + len(BLOB4)
            assert get_repository_size(self.repo1) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(
                BLOB2
            ) + len(BLOB3)
            assert get_repository_size(self.repo2) == len(CONFIG_LAYER_JSON) + len(BLOB1) + len(
                BLOB4
            )

    def test_calculate_registry_size(self, initialized_db):
        QuotaRegistrySize.insert(
            {"size_bytes": 0, "running": False, "queued": True, "completed_ms": None}
        ).execute()
        calculate_registry_size()
        registry_size = get_registry_size()
        assert registry_size is not None
        assert registry_size != 0
        assert registry_size.size_bytes == sum_registry_size()

    def test_queue_registry_size_calculation(self, initialized_db):
        # Queue initial registry size calculation, entry should be created
        queued, already_queued = queue_registry_size_calculation()
        assert queued
        assert not already_queued

        registry_size = get_registry_size()
        assert registry_size is not None
        assert registry_size.queued

        # Assert already queued
        queued, already_queued = queue_registry_size_calculation()
        assert queued
        assert already_queued

        # Assert queued when entry already exists
        QuotaRegistrySize.update({"running": False, "queued": False}).execute()
        queued, already_queued = queue_registry_size_calculation()
        assert queued
        assert not already_queued

        # Assert already queued when total is running
        QuotaRegistrySize.update({"running": True, "queued": False}).execute()
        queued, already_queued = queue_registry_size_calculation()
        assert queued
        assert already_queued


def create_manifest_for_testing(repository, blobs):
    remote_digest = sha256_digest(b"something")
    builder = DockerSchema2ManifestBuilder()
    _, config_digest = _populate_blob(CONFIG_LAYER_JSON, repository.name)
    builder.set_config_digest(config_digest, len(CONFIG_LAYER_JSON.encode("utf-8")))
    builder.add_layer(remote_digest, 1234, urls=["http://hello/world"])

    for blob in blobs:
        _, blob_digest = _populate_blob(blob, repository.name)
        builder.add_layer(blob_digest, len(blob))

    manifest = builder.build()

    created = get_or_create_manifest(repository.id, manifest, storage)
    assert created
    return created.manifest


def _populate_blob(content, repository_name):
    content = Bytes.for_string_or_unicode(content).as_encoded_str()
    digest = str(sha256_digest(content))
    location = ImageStorageLocation.get(name="local_us")
    blob = store_blob_record_and_temp_link(
        ORG_NAME, repository_name, digest, location, len(content), 120
    )
    storage.put_content(["local_us"], get_layer_path(blob), content)
    return blob, digest


def _delete_tag_for_manifest(manifest_id):
    try:
        count = Tag.select().where(Tag.manifest == manifest_id).count()
        assert count == 1
        if count == 0:
            return False
        if count > 1:
            return False
        Tag.delete().where(Tag.manifest == manifest_id).execute()
        return True
    except Tag.DoesNotExist:
        return False
