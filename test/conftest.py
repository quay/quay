import pytest


def pytest_collection_modifyitems(config, items):
    """
    This adds a pytest marker that consistently shards all collected tests.

    Use it like the following:
    $ py.test -m shard_1_of_3
    $ py.test -m shard_2_of_3
    $ py.test -m shard_3_of_3

    This code was originally adopted from the MIT-licensed ansible/molecule@9e7b79b:
    Copyright (c) 2015-2018 Cisco Systems, Inc.
    Copyright (c) 2018 Red Hat, Inc.
    """
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
