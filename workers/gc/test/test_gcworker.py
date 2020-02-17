from workers.gc.gcworker import GarbageCollectionWorker

from test.fixtures import *


def test_gc(initialized_db):
    worker = GarbageCollectionWorker()
    worker._garbage_collection_repos()
