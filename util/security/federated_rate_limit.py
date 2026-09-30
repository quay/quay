"""Distributed rate limiting for public federated robot token exchanges."""

from functools import lru_cache
from hashlib import sha256

from redis import RedisError, StrictRedis


class TokenExchangeRateLimitExceeded(Exception):
    def __init__(self, retry_after):
        self.retry_after = max(retry_after, 1)


class TokenExchangeRateLimitUnavailable(Exception):
    pass


@lru_cache(maxsize=8)
def _redis_client(config_items):
    config = dict(config_items)
    config.setdefault("socket_connect_timeout", 2)
    config.setdefault("socket_timeout", 2)
    return StrictRedis(**config)


def check_token_exchange_rate_limit(redis_config, client_ip, robot_username, limit, window_seconds):
    """Consume one fixed-window exchange allowance for a source IP and robot."""
    identity = "%s\0%s" % (client_ip or "unknown", robot_username)
    key = "federated_robot_token_exchange:%s" % sha256(identity.encode("utf-8")).hexdigest()
    script = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {count, redis.call('TTL', KEYS[1])}
"""
    try:
        count, retry_after = _redis_client(tuple(sorted(redis_config.items()))).eval(
            script, 1, key, window_seconds
        )
    except RedisError as error:
        raise TokenExchangeRateLimitUnavailable() from error

    if int(count) > limit:
        raise TokenExchangeRateLimitExceeded(int(retry_after))
