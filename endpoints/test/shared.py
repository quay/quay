import datetime
import json
import base64

from contextlib import contextmanager
from data import model

from flask import g
from flask_principal import Identity

CSRF_TOKEN_KEY = "_csrf_token"


@contextmanager
def client_with_identity(auth_username, client):
    with client.session_transaction() as sess:
        if auth_username and auth_username is not None:
            loaded = model.user.get_user(auth_username)
            sess["user_id"] = loaded.uuid
            sess["login_time"] = datetime.datetime.now()
        else:
            sess["user_id"] = "anonymous"

    yield client

    with client.session_transaction() as sess:
        sess["user_id"] = None
        sess["login_time"] = None
        sess[CSRF_TOKEN_KEY] = None


@contextmanager
def toggle_feature(name, enabled):
    """
    Context manager which temporarily toggles a feature.
    """
    import features

    previous_value = getattr(features, name)
    setattr(features, name, enabled)
    yield
    setattr(features, name, previous_value)


def add_csrf_param(client, params):
    """
    Returns a params dict with the CSRF parameter added.
    """
    params = params or {}

    with client.session_transaction() as sess:
        params[CSRF_TOKEN_KEY] = "sometoken"
        sess[CSRF_TOKEN_KEY] = "sometoken"

    return params


def gen_basic_auth(username, password):
    """
    Generates a basic auth header.
    """
    encoded_username = username.encode("utf-8")
    encoded_password = password.encode("utf-8")
    return "Basic " + base64.b64encode(b"%s:%s" % (encoded_username, encoded_password)).decode(
        "ascii"
    )


def conduct_call(
    client,
    resource,
    url_for,
    method,
    params,
    body=None,
    expected_code=200,
    headers=None,
    raw_body=None,
):
    """
    Conducts a call to a Flask endpoint.
    """
    params = add_csrf_param(client, params)

    final_url = url_for(resource, **params)

    headers = headers or {}
    headers.update({"Content-Type": "application/json"})

    if body is not None:
        body = json.dumps(body)

    if raw_body is not None:
        body = raw_body

    # Required for anonymous calls to not exception.
    g.identity = Identity(None, "none")

    rv = client.open(final_url, method=method, data=body, headers=headers)
    msg = "%s %s: got %s expected: %s | %s" % (
        method,
        final_url,
        rv.status_code,
        expected_code,
        rv.data,
    )
    assert rv.status_code == expected_code, msg
    return rv
