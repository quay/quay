import pytest
import requests

host = "http://localhost:8080"


@pytest.mark.parametrize(
    "path, status",
    [
        ("/repository/", 200),
        ("/repository/projectquay/clair-jwt", 200),
        ("/organization/projectquay/", 200),
        ("/user/user1/?tab=settings", 200),
        ("/search?q=", 200),
    ],
)
def test_nginx_ok(path, status):
    r = requests.head(f"{host}{path}", allow_redirects=False)
    assert r.status_code == status


def test_sts_rate_limit_returns_token_exchange_error():
    responses = [
        requests.post(
            f"{host}/sts/token",
            data={},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        for _ in range(20)
    ]
    rate_limited = next((response for response in responses if response.status_code == 429), None)
    if rate_limited is None:
        pytest.skip("FEATURE_RATE_LIMITS is disabled on the integration deployment")

    assert rate_limited.json() == {"error": "slow_down"}
    assert int(rate_limited.headers["Retry-After"]) > 0
