from app import namespace_gc_queue
from data import model, database
from workers.namespacegcworker import NamespaceGCWorker

from test.fixtures import *


def test_gc_namespace(initialized_db):
    namespace = model.user.get_namespace_user("buynlarge")
    marker_id = model.user.mark_namespace_for_deletion(namespace, [], namespace_gc_queue)

    assert not database.User.get(id=namespace).enabled

    worker = NamespaceGCWorker(None)
    worker._perform_gc({"marker_id": marker_id})

    assert model.user.get_namespace_user("buynlarge") is None
