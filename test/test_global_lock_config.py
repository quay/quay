from app import _should_configure_global_lock


def test_configures_when_redis_present_and_testing_key_missing():
    config = {"USER_EVENTS_REDIS": {"host": "redis"}}
    assert _should_configure_global_lock(config, is_testing=False) is True


def test_configures_when_redis_present_and_testing_key_true():
    config = {"USER_EVENTS_REDIS": {"host": "redis"}, "TESTING": True}
    assert _should_configure_global_lock(config, is_testing=False) is True


def test_configures_when_testing_key_false():
    config = {"USER_EVENTS_REDIS": {"host": "redis"}, "TESTING": False}
    assert _should_configure_global_lock(config, is_testing=False) is True


def test_does_not_configure_without_redis():
    config = {}
    assert _should_configure_global_lock(config, is_testing=False) is False


def test_does_not_configure_in_test_mode():
    config = {"USER_EVENTS_REDIS": {"host": "redis"}}
    assert _should_configure_global_lock(config, is_testing=True) is False
