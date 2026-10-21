from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest
from itsdangerous import BadSignature, SignatureExpired

from util.fake_checkout import create_session, read_session

SECRET = "QUAY_FIXTURE_ONLY-fake-checkout-signing-key"


def checkout(
    success="http://localhost:9010/organization/example?returned=1",
    cancel="http://localhost:9010/organization/example?canceled=1",
):
    owner = SimpleNamespace(
        uuid="owner", stripe_id="cus_fake_example", organization=True, username="example"
    )
    performer = SimpleNamespace(uuid="actor")
    return create_session(
        SECRET, owner, performer, "subscription", "bus-micro-2018", success, cancel
    )


def test_local_checkout_is_signed_and_bound_to_customer_and_performer():
    result = checkout()
    url = urlsplit(result["url"])
    assert result["fake"] is True
    assert url.netloc == "localhost:9010"
    assert url.path == "/fake-checkout"
    params = parse_qs(url.query)
    assert params["organization"] == ["example"]
    token = params["session"][0]
    payload = read_session(SECRET, token)
    assert payload["owner"] == "owner"
    assert payload["customer"] == "cus_fake_example"
    assert payload["performer"] == "actor"
    assert payload["plan"] == "bus-micro-2018"
    with pytest.raises(BadSignature):
        read_session(SECRET, token + "tampered")
    with patch("itsdangerous.timed.TimestampSigner.get_timestamp", return_value=1):
        expired = checkout()["url"].split("session=")[1].split("&")[0]
    with pytest.raises(SignatureExpired):
        read_session(SECRET, expired)


@pytest.mark.parametrize(
    "success,cancel",
    [
        ("https://quay.io/return", "https://quay.io/cancel"),
        ("http://localhost:9010/return", "https://example.com/cancel"),
        ("http://localhost:9010/return", "http://localhost:9011/cancel"),
        ("http://user@localhost:9010/return", "http://user@localhost:9010/cancel"),
        ("javascript:alert(1)", "javascript:alert(1)"),
    ],
)
def test_fake_checkout_rejects_external_or_mismatched_return_origins(success, cancel):
    with pytest.raises(ValueError):
        checkout(success, cancel)
