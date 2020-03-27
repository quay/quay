import pytest

from mock import patch

from endpoints.api.search import EntitySearch, LinkExternalEntity
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity

from test.test_ldap import mock_ldap
from test.test_external_jwt_authn import fake_jwt
from test.test_keystone_auth import fake_keystone

from test.fixtures import *


@pytest.fixture(
    params=[mock_ldap, fake_jwt, fake_keystone,]
)
def auth_engine(request):
    return request.param


@pytest.fixture(
    params=[False, True,]
)
def requires_email(request):
    return request.param


def test_entity_search(auth_engine, requires_email, client):
    with auth_engine(requires_email=requires_email) as auth:
        with patch("endpoints.api.search.authentication", auth):
            # Try an unknown prefix.
            response = conduct_api_call(client, EntitySearch, "GET", params=dict(prefix="unknown"))
            results = response.json["results"]
            assert len(results) == 0

            # Try a known prefix.
            response = conduct_api_call(client, EntitySearch, "GET", params=dict(prefix="cool"))
            results = response.json["results"]
            entity = results[0]
            assert entity["name"] == "cool.user"
            assert entity["kind"] == "external"


def test_link_external_entity(auth_engine, requires_email, client):
    with auth_engine(requires_email=requires_email) as auth:
        with patch("endpoints.api.search.authentication", auth):
            with client_with_identity("devtable", client) as cl:
                # Try an unknown user.
                conduct_api_call(
                    cl,
                    LinkExternalEntity,
                    "POST",
                    params=dict(username="unknownuser"),
                    expected_code=400,
                )

                # Try a known user.
                response = conduct_api_call(
                    cl, LinkExternalEntity, "POST", params=dict(username="cool.user")
                )

                entity = response.json["entity"]
                assert entity["name"] == "cool_user"
                assert entity["kind"] == "user"
