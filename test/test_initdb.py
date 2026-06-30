from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import initdb


class _MissingModel:
    class DoesNotExist(Exception):
        pass

    @classmethod
    def select(cls):
        return cls

    @classmethod
    def get(cls):
        raise cls.DoesNotExist()


class _PresentModel:
    class DoesNotExist(Exception):
        pass

    @classmethod
    def select(cls):
        return cls

    @classmethod
    def get(cls):
        return object()


class _DeprecatedModel(_MissingModel):
    pass


DeletedNamespace = type("DeletedNamespace", (_MissingModel,), {})


def test_finished_database_for_testing_rolls_back_savepoint_and_transaction():
    testcase = object()
    savepoint = MagicMock()
    transaction = MagicMock()
    initdb.testcases[testcase] = {"savepoint": savepoint, "transaction": transaction}

    initdb.finished_database_for_testing(testcase)

    savepoint.rollback.assert_called_once_with()
    savepoint.__exit__.assert_called_once_with(True, None, None)
    transaction.__exit__.assert_called_once_with(True, None, None)


def test_wipe_database_rejects_non_sqlite_database():
    class NotTheConfiguredSqliteDatabase:
        pass

    with (
        patch("initdb.IS_TESTING_REAL_DATABASE", False),
        patch("initdb.SqliteDatabase", NotTheConfiguredSqliteDatabase),
    ):
        with pytest.raises(RuntimeError, match="production database"):
            initdb.wipe_database()


def test_setup_database_for_testing_rejects_non_sqlite_database():
    class NotTheConfiguredSqliteDatabase:
        pass

    with (
        patch("initdb.IS_TESTING_REAL_DATABASE", False),
        patch("initdb.SqliteDatabase", NotTheConfiguredSqliteDatabase),
    ):
        with pytest.raises(RuntimeError, match="production database"):
            initdb.setup_database_for_testing(object())


def test_find_models_missing_data_ignores_present_whitelisted_and_deprecated_models():
    with (
        patch(
            "initdb.all_models", [_MissingModel, _PresentModel, DeletedNamespace, _DeprecatedModel]
        ),
        patch("initdb.is_deprecated_model", side_effect=lambda model: model is _DeprecatedModel),
    ):
        assert initdb.find_models_missing_data() == {"_MissingModel"}


def _mock_blob(size):
    blob = SimpleNamespace(image_size=size, uploading=True)
    blob.save = MagicMock()
    return blob


def test_create_schema2_manifest_for_testing_stores_blobs_and_tags():
    blobs = []

    def fake_populate_blob(repo, content):
        blob = _mock_blob(len(content))
        blobs.append(blob)
        return blob, "sha256:%s" % len(blobs)

    builder = MagicMock()
    builder.build.return_value = "docker-manifest"
    tag_map = {}

    with (
        patch("initdb._populate_blob", side_effect=fake_populate_blob),
        patch("initdb.RepositoryReference.for_repo_obj", return_value="repo-ref"),
        patch("initdb.get_layer_path", side_effect=lambda blob: ["layer", str(blob.image_size)]),
        patch("initdb.store.put_content") as put_content,
        patch("initdb.DockerSchema2ManifestBuilder", return_value=builder),
        patch(
            "initdb.registry_model.create_manifest_and_retarget_tag",
            return_value=("created-tag", None),
        ) as create_manifest,
    ):
        initdb.create_schema2_or_oci_manifest_for_testing(
            object(), (2, [], "latest"), tag_map, schema_type="docker"
        )

    assert len(blobs) == 3
    assert all(blob.uploading is False for blob in blobs)
    assert put_content.call_count == 3
    builder.set_config_digest.assert_called_once()
    assert builder.add_layer.call_count == 2
    create_manifest.assert_called_once_with(
        "repo-ref", "docker-manifest", "latest", initdb.store, raise_on_error=True
    )
    assert tag_map == {"latest": "created-tag"}


def test_create_oci_manifest_for_testing_uses_oci_builder_and_adjusts_expired_tag():
    def fake_populate_blob(repo, content):
        return _mock_blob(len(content)), "sha256:oci"

    builder = MagicMock()
    builder.build.return_value = "oci-manifest"
    tag_map = {}

    with (
        patch("initdb._populate_blob", side_effect=fake_populate_blob),
        patch("initdb.RepositoryReference.for_repo_obj", return_value="repo-ref"),
        patch("initdb.get_layer_path", return_value=["layer"]),
        patch("initdb.store.put_content"),
        patch("initdb.OCIManifestBuilder", return_value=builder),
        patch("initdb.OCIConfig", return_value="oci-config"),
        patch("initdb.Bytes.for_string_or_unicode", return_value="config-bytes"),
        patch(
            "initdb.registry_model.create_manifest_and_retarget_tag",
            return_value=("created-tag", None),
        ) as create_manifest,
    ):
        initdb.create_schema2_or_oci_manifest_for_testing(
            object(), (1, [], "#old"), tag_map, schema_type="oci"
        )

    builder.set_config.assert_called_once_with("oci-config")
    builder.add_layer.assert_called_once()
    create_manifest.assert_called_once_with(
        "repo-ref", "oci-manifest", "old", initdb.store, raise_on_error=True
    )
    assert tag_map == {"old": "created-tag"}
