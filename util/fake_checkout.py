"""Signed, local-only checkout links for the FakeStripe development provider."""

import uuid
from urllib.parse import urlencode, urlsplit

from itsdangerous import URLSafeTimedSerializer


def serializer(secret):
    return URLSafeTimedSerializer(secret, salt="quay-fake-checkout")


def create_session(secret, owner, performer, mode, plan, success_url, cancel_url):
    success = urlsplit(success_url)
    cancel = urlsplit(cancel_url)
    if (
        success.scheme not in ("http", "https")
        or success.hostname not in ("localhost", "127.0.0.1", "::1")
        or success.username
        or success.password
        or (success.scheme, success.netloc) != (cancel.scheme, cancel.netloc)
    ):
        raise ValueError("Fake checkout requires matching local return URLs.")
    token = serializer(secret).dumps(
        {
            "id": str(uuid.uuid4()),
            "owner": owner.uuid,
            "customer": owner.stripe_id,
            "performer": performer.uuid,
            "mode": mode,
            "plan": plan,
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
    )
    query = {"session": token}
    if owner.organization:
        query["organization"] = owner.username
    return {
        "url": f"{success.scheme}://{success.netloc}/fake-checkout?{urlencode(query)}",
        "fake": True,
    }


def read_session(secret, token):
    return serializer(secret).loads(token, max_age=3600)
