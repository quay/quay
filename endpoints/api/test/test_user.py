import pytest

from mock import patch

from endpoints.api.test.shared import conduct_api_call
from endpoints.api.user import User
from endpoints.test.shared import client_with_identity
from features import FeatureNameValue

from test.fixtures import *


def test_user_metadata_update(client):
    with patch("features.USER_METADATA", FeatureNameValue("USER_METADATA", True)):
        with client_with_identity("devtable", client) as cl:
            metadata = {
                "given_name": "Quay",
                "family_name": "User",
                "location": "NYC",
                "company": "Red Hat",
            }

            # Update all user metadata fields.
            conduct_api_call(cl, User, "PUT", None, body=metadata)

            # Test that they were successfully updated.
            user = conduct_api_call(cl, User, "GET", None).json
            for field in metadata:
                assert user.get(field) == metadata.get(field)

            # Now nullify one of the fields, and remove another.
            metadata["company"] = None
            location = metadata.pop("location")

            conduct_api_call(cl, User, "PUT", None, body=metadata)

            user = conduct_api_call(cl, User, "GET", None).json
            for field in metadata:
                assert user.get(field) == metadata.get(field)

            # The location field should be unchanged.
            assert user.get("location") == location
