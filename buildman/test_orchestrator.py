import time
import pytest
from random import randrange
from unittest.mock import patch, Mock

import fakeredis
from freezegun import freeze_time

from buildman.orchestrator import MemoryOrchestrator, RedisOrchestrator, REDIS_EXPIRED_SUFFIX, REDIS_EXPIRING_SUFFIX, KeyEvent, KeyChange
from util import slash_join

from test.fixtures import *


@pytest.fixture()
def fake_redis():
    def init_fake_strict_redis(
            host="127.0.0.1",
            port=6379,
            password=None,
            db=0,
            ssl_certfile=None,
            ssl_keyfile=None,
            ssl_ca_certs=None,
            ssl=False,
            socket_connect_timeout=1,
            socket_timeout=2,
            health_check_interval=2,
    ):
        fake_client = fakeredis.FakeStrictRedis(
            host=host,
            port=port,
            password=password,
            db=db,
            ssl_certfile=ssl_certfile,
            ssl_keyfile=ssl_keyfile,
            ssl_ca_certs=ssl_ca_certs,
            ssl=ssl,
            socket_connect_timeout=socket_connect_timeout,
            socket_timeout=socket_timeout,
            # health_check_interval is not supported by fakeredis on its StrictRedis interface
        )
        fake_client.config_set = Mock()

        fake_client.flushall()
        return fake_client

    with patch("redis.StrictRedis", init_fake_strict_redis):
        yield


@pytest.fixture(params=[MemoryOrchestrator, RedisOrchestrator])
def orchestrator(request, fake_redis):
    return request.param()


def test_acquire_lock(orchestrator):
    lock_key = "lock/somekey"
    acquired = orchestrator.lock(lock_key)
    assert acquired
    assert orchestrator.get_key(lock_key) is not None

    acquired_again = orchestrator.lock(lock_key)
    assert not acquired_again

    orchestrator.delete_key(lock_key)
    assert orchestrator.lock(lock_key)


def test_get_prefixed_keys(orchestrator):
    keys_to_generate = 10
    key_prefix = "building/"

    generated_keys = set()
    for x in range(keys_to_generate):
        orchestrator.set_key(slash_join(key_prefix, str(x)), "test_val")
        generated_keys.add(slash_join(key_prefix, str(x)))
        
    assert len(orchestrator.get_prefixed_keys(key_prefix)) == keys_to_generate
        
    keys_to_remove = randrange(1, keys_to_generate)
    for x in range(keys_to_remove):
        orchestrator.delete_key(slash_join(key_prefix, str(x)))
        generated_keys.remove(slash_join(key_prefix, str(x)))
    
    assert len(orchestrator.get_prefixed_keys(key_prefix)) == keys_to_generate - keys_to_remove

    for k in generated_keys:
       orchestrator.delete_key(k)
    assert len(orchestrator.get_prefixed_keys(key_prefix)) == 0


def test_set_key(orchestrator):
    some_key = "someprefix/somekey"

    # Setting overwrite if the key doesn't exists prevent it from being written
    orchestrator.set_key(some_key, "test_val", overwrite=True)
    with pytest.raises(KeyError):
        orchestrator.get_key(some_key)

    # Set some key/value
    orchestrator.set_key(some_key, "test_val_2")
    assert orchestrator.get_key(some_key) == "test_val_2"

    # Try overwriting some existing key without setting overwrite
    with pytest.raises(KeyError):
        orchestrator.set_key(some_key, "test_val_3")
    
    # Try overwriting some existing key with overwrite set.
    # Also expects a new expiration key to be created.
    orchestrator.set_key(some_key, "test_val_4", overwrite=True, expiration=360)
    assert orchestrator.get_key(some_key) == "test_val_4"
    assert orchestrator.get_key(slash_join(some_key, REDIS_EXPIRING_SUFFIX)) is not None
    

def test_on_key_change(orchestrator):
    key_prefix = "building/"
    mock_callback = Mock()

    orchestrator.on_key_change(key_prefix, lambda x: mock_callback.meth(x))

    # CREATE
    orchestrator.set_key(slash_join(key_prefix, "key1"), "test_val")
    time.sleep(0.1)
    mock_callback.meth.assert_called_with(
        KeyChange(
            KeyEvent.CREATE,
            slash_join(key_prefix, "key1"),
            "test_val",
        )
    )
    
    # SET
    orchestrator.set_key(slash_join(key_prefix, "key1"), "test_val", overwrite=True)
    time.sleep(0.1)
    mock_callback.meth.assert_called_with(
        KeyChange(
            KeyEvent.SET,
            slash_join(key_prefix, "key1"),
            "test_val",
        )
    )

    # DELETE
    orchestrator.delete_key(slash_join(key_prefix, "key1"))
    time.sleep(0.1)
    mock_callback.meth.assert_called_with(
        KeyChange(
            KeyEvent.DELETE,
            slash_join(key_prefix, "key1"),
            "test_val",
        )
    )


def test_get_key(orchestrator):
    key_prefix = "building/"

    with pytest.raises(KeyError):
        orchestrator.get_key(slash_join(key_prefix, "key1"))

    orchestrator.set_key(slash_join(key_prefix, "key1"), "test_val", overwrite=True)
    with pytest.raises(KeyError):
        orchestrator.get_key(slash_join(key_prefix, "key1"))

    orchestrator.set_key(slash_join(key_prefix, "key1"), "test_val")
    assert orchestrator.get_key(slash_join(key_prefix, "key1")) == "test_val"


def test_delete_key(orchestrator):
    key_prefix = "building/"

    with pytest.raises(KeyError):
        orchestrator.delete_key(slash_join(key_prefix, "key1"))

    orchestrator.set_key(slash_join(key_prefix, "key1"), "test_val")
    assert orchestrator.get_key(slash_join(key_prefix, "key1")) is not None

    orchestrator.delete_key(slash_join(key_prefix, "key1"))
    with pytest.raises(KeyError):
        orchestrator.get_key(slash_join(key_prefix, "key1"))
        
