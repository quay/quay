import pytest

from app import apply_storage_replication_config


def test_env_var_overrides_missing_config(monkeypatch):
    monkeypatch.setenv("QUAY_DISTRIBUTED_STORAGE_PREFERENCE", "us_east eu_west")
    config = {"FEATURE_STORAGE_REPLICATION": True}
    apply_storage_replication_config(config)
    assert config["DISTRIBUTED_STORAGE_PREFERENCE"] == ["us_east", "eu_west"]


def test_env_var_overrides_existing_config(monkeypatch):
    monkeypatch.setenv("QUAY_DISTRIBUTED_STORAGE_PREFERENCE", "us_east eu_west")
    config = {
        "FEATURE_STORAGE_REPLICATION": True,
        "DISTRIBUTED_STORAGE_PREFERENCE": ["eu_central"],
    }
    apply_storage_replication_config(config)
    assert config["DISTRIBUTED_STORAGE_PREFERENCE"] == ["us_east", "eu_west"]


def test_config_preference_sufficient_without_env_var(monkeypatch):
    monkeypatch.delenv("QUAY_DISTRIBUTED_STORAGE_PREFERENCE", raising=False)
    config = {
        "FEATURE_STORAGE_REPLICATION": True,
        "DISTRIBUTED_STORAGE_PREFERENCE": ["us_east"],
    }
    apply_storage_replication_config(config)


def test_raises_without_any_preference(monkeypatch):
    monkeypatch.delenv("QUAY_DISTRIBUTED_STORAGE_PREFERENCE", raising=False)
    config = {"FEATURE_STORAGE_REPLICATION": True}
    with pytest.raises(Exception, match="Missing storage preference"):
        apply_storage_replication_config(config)


def test_raises_with_empty_preference_list(monkeypatch):
    monkeypatch.delenv("QUAY_DISTRIBUTED_STORAGE_PREFERENCE", raising=False)
    config = {
        "FEATURE_STORAGE_REPLICATION": True,
        "DISTRIBUTED_STORAGE_PREFERENCE": [],
    }
    with pytest.raises(Exception, match="Missing storage preference"):
        apply_storage_replication_config(config)


def test_replication_disabled_skips_validation(monkeypatch):
    monkeypatch.delenv("QUAY_DISTRIBUTED_STORAGE_PREFERENCE", raising=False)
    apply_storage_replication_config({"FEATURE_STORAGE_REPLICATION": False})
    apply_storage_replication_config({})
