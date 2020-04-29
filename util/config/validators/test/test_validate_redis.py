import pytest
import redis

from mock import patch

from fakeredis import FakeStrictRedis

from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_redis import RedisValidator

from test.fixtures import *
from util.morecollections import AttrDict


@pytest.mark.parametrize(
    "unvalidated_config,user,user_password,use_mock,expected",
    [
        ({}, None, None, False, ConfigValidationException),
        ({"BUILDLOGS_REDIS": {}}, None, None, False, ConfigValidationException),
        ({"BUILDLOGS_REDIS": {"host": "somehost"}}, None, None, False, redis.ConnectionError),
        ({"BUILDLOGS_REDIS": {"host": "localhost"}}, None, None, True, None),
    ],
)
def test_validate_redis(unvalidated_config, user, user_password, use_mock, expected, app):
    with patch("redis.StrictRedis" if use_mock else "redis.None", FakeStrictRedis):
        validator = RedisValidator()
        unvalidated_config = ValidatorContext(unvalidated_config)

        unvalidated_config.user = AttrDict(dict(username=user))
        unvalidated_config.user_password = user_password

        if expected is not None:
            with pytest.raises(expected):
                validator.validate(unvalidated_config)
        else:
            validator.validate(unvalidated_config)
