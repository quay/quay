import pytest

INTEGRATION_FIXTURES = {"initialized_db", "app", "appconfig", "database_uri", "init_db_path"}

# Tests that don't use standard DB fixtures but import from app or data.users,
# which triggers the full app import chain and can cause circular imports
# when run in isolation from the rest of the test suite.
INTEGRATION_FILES = {
    "test_anon_checked.py",
    "test_csrf.py",
    "test_determine_auth_type.py",
    "test_log_action_feature_flag.py",
    "test_log_util.py",
    "test_manifest.py",
    "test_oci_tag.py",
    "test_oidc.py",
    "test_reconciliationworker.py",
    "test_request_redirect.py",
    "test_schema1.py",
    "test_secscan_v4_model.py",
    "test_superusermanager.py",
}

LEGACY_FILES = {
    "test_api_usage.py",
    "test_endpoints.py",
    "test_external_jwt_authn.py",
    "test_external_oidc.py",
    "test_keystone_auth.py",
    "test_ldap.py",
    "test_oauth_login.py",
    "test_registry_jwt.py",
    "test_v1_endpoint_security.py",
    "test_v2_endpoint_security.py",
}


def pytest_collection_modifyitems(config, items):
    """
    Classifies tests and adds shard markers for CI parallelization.

    - ``legacy``: unittest.TestCase tests with SQLite locking issues under xdist
    - ``integration``: tests that use database/Flask fixtures
    - Remaining unmarked tests are true unit tests (no DB)

    Sharding (unchanged from original):
        $ py.test -m shard_1_of_3
        $ py.test -m shard_2_of_3
        $ py.test -m shard_3_of_3

    This code was originally adopted from the MIT-licensed ansible/molecule@9e7b79b:
    Copyright (c) 2015-2018 Cisco Systems, Inc.
    Copyright (c) 2018 Red Hat, Inc.
    """
    for item in items:
        if item.fspath.basename in LEGACY_FILES:
            item.add_marker(pytest.mark.legacy)
        elif item.fspath.basename in INTEGRATION_FILES or INTEGRATION_FIXTURES & set(
            item.fixturenames
        ):
            item.add_marker(pytest.mark.integration)

    mark_opt = config.getoption("-m")
    if not mark_opt.startswith("shard_"):
        return

    desired_shard, _, total_shards = mark_opt[len("shard_") :].partition("_of_")
    if not total_shards or not desired_shard:
        return

    desired_shard = int(desired_shard)
    total_shards = int(total_shards)

    if not 0 < desired_shard <= total_shards:
        raise ValueError("desired_shard must be greater than 0 and not bigger than total_shards")

    for test_counter, item in enumerate(items):
        shard = test_counter % total_shards + 1
        marker = getattr(pytest.mark, "shard_{}_of_{}".format(shard, total_shards))
        item.add_marker(marker)

    print("Running sharded test group #{} out of {}".format(desired_shard, total_shards))
