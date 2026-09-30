from unittest.mock import MagicMock

import pytest

from util.security import federated_rate_limit


def test_rate_limit_is_scoped_to_source_ip_and_robot(monkeypatch):
    client = MagicMock()
    client.eval.side_effect = [(1, 60), (2, 60), (3, 59), (1, 60), (1, 60)]
    monkeypatch.setattr(federated_rate_limit, "_redis_client", lambda _config: client)
    redis_config = {"host": "redis"}

    for _ in range(2):
        federated_rate_limit.check_token_exchange_rate_limit(
            redis_config, "192.0.2.1", "acme+robot", 2, 60
        )

    with pytest.raises(federated_rate_limit.TokenExchangeRateLimitExceeded) as error:
        federated_rate_limit.check_token_exchange_rate_limit(
            redis_config, "192.0.2.1", "acme+robot", 2, 60
        )

    assert error.value.retry_after == 59
    federated_rate_limit.check_token_exchange_rate_limit(
        redis_config, "192.0.2.2", "acme+robot", 2, 60
    )
    federated_rate_limit.check_token_exchange_rate_limit(
        redis_config, "192.0.2.1", "acme+another-robot", 2, 60
    )

    keys = [call.args[2] for call in client.eval.call_args_list]
    assert len(set(keys)) == 3
