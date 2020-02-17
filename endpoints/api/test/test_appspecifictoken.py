from datetime import datetime, timedelta

from data import model
from endpoints.api.appspecifictokens import AppTokens, AppToken
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


def test_app_specific_tokens(app, client):
    with client_with_identity("devtable", client) as cl:
        # Add an app specific token.
        token_data = {"title": "Testing 123"}
        resp = conduct_api_call(cl, AppTokens, "POST", None, token_data, 200).json
        token_uuid = resp["token"]["uuid"]
        assert "token_code" in resp["token"]

        # List the tokens and ensure we have the one added.
        resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200).json
        assert len(resp["tokens"])
        assert token_uuid in set([token["uuid"] for token in resp["tokens"]])
        assert not set([token["token_code"] for token in resp["tokens"] if "token_code" in token])

        # List the tokens expiring soon and ensure the one added is not present.
        resp = conduct_api_call(cl, AppTokens, "GET", {"expiring": True}, None, 200).json
        assert token_uuid not in set([token["uuid"] for token in resp["tokens"]])

        # Get the token and ensure we have its code.
        resp = conduct_api_call(cl, AppToken, "GET", {"token_uuid": token_uuid}, None, 200).json
        assert resp["token"]["uuid"] == token_uuid
        assert "token_code" in resp["token"]

        # Delete the token.
        conduct_api_call(cl, AppToken, "DELETE", {"token_uuid": token_uuid}, None, 204)

        # Ensure the token no longer exists.
        resp = conduct_api_call(cl, AppTokens, "GET", None, None, 200).json
        assert len(resp["tokens"])
        assert token_uuid not in set([token["uuid"] for token in resp["tokens"]])

        conduct_api_call(cl, AppToken, "GET", {"token_uuid": token_uuid}, None, 404)


def test_delete_expired_app_token(app, client):
    user = model.user.get_user("devtable")
    expiration = datetime.now() - timedelta(seconds=10)
    token = model.appspecifictoken.create_token(user, "some token", expiration)

    with client_with_identity("devtable", client) as cl:
        # Delete the token.
        conduct_api_call(cl, AppToken, "DELETE", {"token_uuid": token.uuid}, None, 204)
