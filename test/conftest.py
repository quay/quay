import sys

import pytest

INTEGRATION_FIXTURES = {"initialized_db", "app", "appconfig", "database_uri", "init_db_path"}

# Module prefixes that indicate a test depends on the app import chain.
# Tests importing (directly or transitively) from these are auto-promoted
# to integration so they don't run in the isolated unit job.
_APP_MODULE_PREFIXES = ("app", "app.", "data.users", "data.users.")

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
        elif INTEGRATION_FIXTURES & set(item.fixturenames):
            item.add_marker(pytest.mark.integration)

    # Auto-promote: catch unclassified tests whose module imports from the app
    # tree. Checks both the __module__ of imported objects and the module's
    # direct dependencies in sys.modules to handle transitive imports.
    _seen_modules = {}
    for item in items:
        if item.get_closest_marker("integration") or item.get_closest_marker("legacy"):
            continue
        module = getattr(item, "module", None)
        if module is None:
            continue
        mod_name = module.__name__
        if mod_name not in _seen_modules:
            has_app = False
            for obj in module.__dict__.values():
                obj_mod = getattr(obj, "__module__", None) or ""
                if obj_mod.startswith(_APP_MODULE_PREFIXES):
                    has_app = True
                    break
            if not has_app:
                # Check if the module caused app-level modules to load by
                # inspecting its direct imports via the module's global names.
                for name, obj in module.__dict__.items():
                    if isinstance(obj, type(sys)) and getattr(obj, "__name__", "").startswith(
                        _APP_MODULE_PREFIXES
                    ):
                        has_app = True
                        break
            _seen_modules[mod_name] = has_app
        if _seen_modules[mod_name]:
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
