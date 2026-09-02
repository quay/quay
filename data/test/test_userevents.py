import uuid
from unittest.mock import patch

import fakeredis
import pytest

from data.userevent import UserEvent, UserEventBuilder, UserEventListener


@pytest.fixture
def fake_redis():
    def init_fake_strict_redis(*args, **kwargs):
        return fakeredis.FakeStrictRedis()

    with patch("redis.StrictRedis", init_fake_strict_redis):
        yield


def test_builder_creates_shared_client():
    """
    Verifies that we create one pool of connections for the user events that is then
    shared across Redis requests.
    """
    with patch("redis.StrictRedis", wraps=fakeredis.FakeStrictRedis) as mock_redis:
        builder = UserEventBuilder({"host": "localhost"})

        # two events must share the same client
        e1 = builder.get_event("ivan")
        e2 = builder.get_event("foo")

        # assert that both have the same config
        assert mock_redis.call_count == 1
        assert e1._redis is e2._redis
        assert e1._redis is builder.client


def test_publish_event_through_shared_client():
    """
    Verifies that publishing of the events works.
    """
    server = fakeredis.FakeServer()

    def make_client(*args, **kwargs):
        return fakeredis.FakeStrictRedis(server=server)

    with patch("redis.StrictRedis", make_client):
        builder = UserEventBuilder({"host": "localhost"})

        # create a new event
        event_data = {"msg": "test event"}
        eid = str(uuid.uuid4())

        # define the listener
        listener = UserEventListener({"host": "localhost"}, "alice", {eid})

        # publish event
        publisher = builder.get_event("alice")
        received_by = publisher.publish_event_data_sync(eid, event_data)
        assert received_by == 1

        # read data back
        for received_id, data in listener.event_stream():
            if received_id == "pulse":
                continue
            assert received_id == eid
            assert data == event_data
            break

        listener.stop()
