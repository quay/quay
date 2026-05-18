import json
from unittest.mock import MagicMock, patch

import pytest
from mock import call
from playhouse.test_utils import assert_query_count

from app import storage
from data.database import ImageStorageLocation, QuotaRegistrySize, Tag
from data.model.blob import store_blob_record_and_temp_link
from data.model.gc import _garbage_collect_manifest, _GarbageCollectorContext
from data.model.namespacequota import get_namespace_size
from data.model.oci.manifest import get_or_create_manifest
from data.model.organization import create_organization
from data.model.quota import QuotaOperation, calculate_registry_size
from data.model.quota import get_namespace_size as get_namespace_size_row
from data.model.quota import get_registry_size
from data.model.quota import get_repository_size as get_repository_size_row
from data.model.quota import (
    queue_registry_size_calculation,
    run_backfill,
    sum_registry_size,
    update_quota,
)
from data.model.repository import create_repository, get_repository_size
from data.model.storage import get_layer_path
from data.model.user import get_namespace_user_by_user_id, get_user
from digest.digest_tools import sha256_digest
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from test.fixtures import *
from util.bytes import Bytes

ORG_NAME = "org1"
ORG2_NAME = "org2"
REPO1_NAME = "repo1"
REPO2_NAME = "repo2"
REPO3_NAME = "repo3"
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
        with patch("data.model.quota.features", MagicMock()) as mock_features:
            mock_features.QUOTA_MANAGEMENT = False
            user = get_user("devtable")
            self.org = create_organization(ORG_NAME, f"{ORG_NAME}@devtable.com", user)
            self.repo1 = create_repository(ORG_NAME, REPO1_NAME, user)
            self.repo1manifest1 = create_manifest_for_testing(self.repo1, [BLOB1, BLOB2])
            self.repo1manifest2 = create_manifest_for_testing(self.repo1, [BLOB1, BLOB3])
            self.repo2 = create_repository(ORG_NAME, REPO2_NAME, user)
            self.repo2manifest3 = create_manifest_for_testing(self.repo2, [BLOB1, BLOB4])
            self.org2 = create_organization(ORG2_NAME, f"{ORG2_NAME}@devtable.com", user)
            self.org2repo1 = create_repository(ORG2_NAME, REPO1_NAME, user)
            self.org2repo1manifest1 = create_manifest_for_testing(self.org2repo1, [BLOB1, BLOB2])

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

    def test_invalidate_size(self, initialized_db):
        run_backfill(self.org.id)
        namespace_size = get_namespace_size_row(self.org.id)
        assert namespace_size.size_bytes != 0
        assert namespace_size.backfill_start_ms is not None
        assert namespace_size.backfill_complete
        repo_size = get_repository_size_row(self.repo1.id)
        assert repo_size.size_bytes != 0
        assert repo_size.backfill_start_ms is not None
        assert repo_size.backfill_complete

        # check backfill was reset by default if quota is not enabled
        with patch("data.model.quota.features", MagicMock()) as mock_features:
            mock_features.QUOTA_MANAGEMENT = False
            update_quota(self.repo1.id, self.repo1manifest1.id, {}, QuotaOperation.ADD)
            namespace_size = get_namespace_size_row(self.org.id)
            assert namespace_size.size_bytes == 0
            assert namespace_size.backfill_start_ms is None
            assert not namespace_size.backfill_complete
            repo_size = get_repository_size_row(self.repo1.id)
            assert repo_size.size_bytes == 0
            assert repo_size.backfill_start_ms is None
            assert not repo_size.backfill_complete

        # check that backfill was not reset if QUOTA_INVALIDATE_TOTALS is disabled
        with patch("data.model.quota.features", MagicMock()) as mock_features:
            with patch("data.model.quota.config.app_config", {"QUOTA_INVALIDATE_TOTALS": False}):
                mock_features.QUOTA_MANAGEMENT = False
                with patch("data.model.quota.reset_backfill", MagicMock()) as mock_reset_backfill:
                    update_quota(self.repo1.id, self.repo1manifest1.id, {}, QuotaOperation.ADD)
                    assert not mock_reset_backfill.called

    def test_suppress_failures(self, initialized_db):
        run_backfill(self.org.id)

        # assert that an exception is caught and logged when QUOTA_SUPPRESS_FAILURES is enabled
        with patch("data.model.quota.features", MagicMock()) as mock_features:
            mock_features.QUOTA_MANAGEMENT = True
            mock_features.QUOTA_SUPPRESS_FAILURES = True
            with patch("data.model.quota.update_sizes", side_effect=Exception("mock error")):
                with patch("data.model.quota.logger.exception", MagicMock()) as mock_logger:
                    update_quota(self.repo1.id, self.repo1manifest1.id, {}, QuotaOperation.ADD)
                    mock_logger.assert_called_once()

        # assert exceptions are not suppressed by default
        with patch("data.model.quota.update_sizes", side_effect=Exception("mock error")):
            with pytest.raises(Exception) as exinfo:
                update_quota(self.repo1.id, self.repo1manifest1.id, {}, QuotaOperation.ADD)
            assert str(exinfo.value) == "mock error"

    def test_update_size_no_blobs(self, initialized_db):
        run_backfill(self.org.id)

        with assert_query_count(0):
            with patch("data.model.quota.logger.debug", MagicMock()) as mock_logger:
                update_quota(self.repo1.id, self.repo1manifest1.id, {}, QuotaOperation.ADD)
                assert mock_logger.call_args[0] == (
                    "no blobs found for manifest %s in repository %s, skipping calculation",
                    self.repo1manifest1.id,
                    self.repo1.id,
                )

    def test_ineligible_namespace_disabled(self, initialized_db):
        run_backfill(self.org.id)

        self.org.enabled = False
        self.org.save()

        with assert_query_count(2):
            with patch("data.model.quota.logger.debug", MagicMock()) as mock_logger:
                update_quota(self.repo1.id, self.repo1manifest1.id, {1: 10}, QuotaOperation.ADD)
                assert mock_logger.call_args[0] == (
                    "ineligible namespace %s for quota calculation, skipping calculation",
                    self.org.id,
                )

    def test_ineligible_namespace_robot(self, initialized_db):
        run_backfill(self.org.id)

        self.org.robot = True
        self.org.save()

        with assert_query_count(2):
            with patch("data.model.quota.logger.debug", MagicMock()) as mock_logger:
                update_quota(self.repo1.id, self.repo1manifest1.id, {1: 10}, QuotaOperation.ADD)
                assert mock_logger.call_args[0] == (
                    "ineligible namespace %s for quota calculation, skipping calculation",
                    self.org.id,
                )

    def test_only_manifest_in_namespace_and_repo(self, initialized_db):
        namespace_size_row = get_namespace_size_row(self.org2.id)
        assert namespace_size_row is None
        repository_size_row = get_repository_size_row(self.org2repo1.id)
        assert repository_size_row is None

        with assert_query_count(10):
            with patch("data.model.quota.logger.info", MagicMock()) as mock_logger:
                update_quota(
                    self.org2repo1.id,
                    self.org2repo1manifest1.id,
                    {1: 10, 2: 20},
                    QuotaOperation.ADD,
                )
                assert mock_logger.call_args_list[0] == call(
                    "inserting namespace size for manifest %s in namespace %s",
                    self.org2repo1manifest1.id,
                    self.org2.id,
                )
                assert mock_logger.call_args_list[1] == call(
                    "inserting repository size for manifest %s in repository %s",
                    self.org2repo1manifest1.id,
                    self.org2repo1.id,
                )

        assert get_namespace_size("org2") == 30
        assert get_repository_size(self.org2repo1.id) == 30

    def test_namespace_and_repo_require_backfill(self, initialized_db):
        org2repo1manifest2 = create_manifest_for_testing(self.org2repo1, [BLOB1, BLOB3])
        namespace_size_row = get_namespace_size_row(self.org2.id)
        assert namespace_size_row is None
        repository_size_row = get_repository_size_row(self.org2repo1.id)
        assert repository_size_row is None

        with assert_query_count(8):
            with patch("data.model.quota.logger.info", MagicMock()) as mock_logger:
                update_quota(
                    self.org2repo1.id, org2repo1manifest2.id, {1: 10, 2: 20}, QuotaOperation.ADD
                )
                assert mock_logger.call_args_list[0] == call(
                    "backfill required for manifest %s in namespace %s",
                    org2repo1manifest2.id,
                    self.org2.id,
                )
                assert mock_logger.call_args_list[1] == call(
                    "backfill required for manifest %s in repository %s",
                    org2repo1manifest2.id,
                    self.org2repo1.id,
                )

        namespace_size_row = get_namespace_size_row(self.org2.id)
        assert namespace_size_row is None
        repository_size_row = get_repository_size_row(self.org2repo1.id)
        assert repository_size_row is None

    @pytest.mark.parametrize(
        "blobs, operation, expected_namespace_difference, expected_repository_difference",
        [
            (
                [BLOB5, BLOB6],
                QuotaOperation.ADD,
                len(BLOB5) + len(BLOB6),
                len(BLOB5) + len(BLOB6),
            ),  # 2 blobs new to both namespace and repo
            ([BLOB1, BLOB4], QuotaOperation.ADD, 0, 0),  # 2 blobs existing in namespace and repo
            (
                [BLOB1, BLOB5],
                QuotaOperation.ADD,
                len(BLOB5),
                len(BLOB5),
            ),  # One existing and one new to the namespace and repo
            (
                [BLOB2, BLOB3],
                QuotaOperation.ADD,
                0,
                len(BLOB2) + len(BLOB3),
            ),  # Both new to the repository but not to the namespace
            (
                [BLOB5, BLOB6],
                QuotaOperation.SUBTRACT,
                len(BLOB5) + len(BLOB6),
                len(BLOB5) + len(BLOB6),
            ),  # 2 blobs new to both namespace and repo
            (
                [BLOB1, BLOB4],
                QuotaOperation.SUBTRACT,
                0,
                0,
            ),  # 2 blobs existing in namespace and repo
            (
                [BLOB1, BLOB5],
                QuotaOperation.SUBTRACT,
                len(BLOB5),
                len(BLOB5),
            ),  # One existing and one new to the namespace and repo
            (
                [BLOB2, BLOB3],
                QuotaOperation.SUBTRACT,
                0,
                len(BLOB2) + len(BLOB3),
            ),  # Both new to the repository but not to the namespace
        ],
    )
    def test_namespace_and_repo_backfilled(
        self,
        blobs,
        operation,
        expected_namespace_difference,
        expected_repository_difference,
        initialized_db,
    ):
        run_backfill(self.org.id)
        namespace_size_before = get_namespace_size_row(self.org.id).size_bytes
        repository_size_before = get_repository_size_row(self.repo2.id).size_bytes
        assert namespace_size_before != 0
        assert repository_size_before != 0

        create_manifest_for_testing(self.repo2, blobs)

        assert (
            get_namespace_size(self.org.username)
            == namespace_size_before + expected_namespace_difference
            if operation == QuotaOperation.ADD
            else namespace_size_before - expected_namespace_difference
        )
        assert (
            get_repository_size(self.repo2)
            == repository_size_before + expected_repository_difference
            if operation == QuotaOperation.ADD
            else repository_size_before - expected_repository_difference
        )


def create_manifest_for_testing(repository, blobs):
    remote_digest = sha256_digest(b"something")
    builder = DockerSchema2ManifestBuilder()
    namespace = get_namespace_user_by_user_id(repository.namespace_user)
    _, config_digest = _populate_blob(CONFIG_LAYER_JSON, namespace.username, repository.name)
    builder.set_config_digest(config_digest, len(CONFIG_LAYER_JSON.encode("utf-8")))
    builder.add_layer(remote_digest, 1234, urls=["http://hello/world"])
    for blob in blobs:
        _, blob_digest = _populate_blob(blob, namespace.username, repository.name)
        builder.add_layer(blob_digest, len(blob))

    manifest = builder.build()

    created = get_or_create_manifest(repository.id, manifest, storage)
    assert created
    return created.manifest


def _populate_blob(content, namespace_name, repository_name):
    content = Bytes.for_string_or_unicode(content).as_encoded_str()
    digest = str(sha256_digest(content))
    location = ImageStorageLocation.get(name="local_us")
    blob = store_blob_record_and_temp_link(
        namespace_name, repository_name, digest, location, len(content), 120
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
