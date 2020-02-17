import redis

from util.config.validators import BaseValidator, ConfigValidationException


class RedisValidator(BaseValidator):
    name = "redis"

    @classmethod
    def validate(cls, validator_context):
        """
        Validates connecting to redis.
        """
        config = validator_context.config

        redis_config = config.get("BUILDLOGS_REDIS", {})
        if not "host" in redis_config:
            raise ConfigValidationException("Missing redis hostname")

        client = redis.StrictRedis(socket_connect_timeout=5, **redis_config)
        client.ping()
