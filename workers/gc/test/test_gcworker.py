from test.fixtures import *

from workers.gc.gcworker import GarbageCollectionWorker


def test_gc(initialized_db):
    worker = GarbageCollectionWorker()
    worker._garbage_collection_repos(skip_lock_for_testing=True)
