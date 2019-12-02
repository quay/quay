import pytest

from collections import Counter
from mock import patch

from endpoints.api.test.shared import conduct_api_call
from endpoints.api.signing import RepositorySignatures
from endpoints.test.shared import client_with_identity

from test.fixtures import *

VALID_TARGETS_MAP = {
    "targets/ci": {
        "targets": {
            "latest": {
                "hashes": {"sha256": "2Q8GLEgX62VBWeL76axFuDj/Z1dd6Zhx0ZDM6kNwPkQ="},
                "length": 2111,
            }
        },
        "expiration": "2020-05-22T10:26:46.618176424-04:00",
    },
    "targets": {
        "targets": {
            "latest": {
                "hashes": {"sha256": "2Q8GLEgX62VBWeL76axFuDj/Z1dd6Zhx0ZDM6kNwPkQ="},
                "length": 2111,
            }
        },
        "expiration": "2020-05-22T10:26:01.953414888-04:00",
    },
}


def tags_equal(expected, actual):
    expected_tags = expected.get("delegations")
    actual_tags = actual.get("delegations")
    if expected_tags and actual_tags:
        return Counter(expected_tags) == Counter(actual_tags)
    return expected == actual


@pytest.mark.parametrize(
    "targets_map,expected",
    [
        (VALID_TARGETS_MAP, {"delegations": VALID_TARGETS_MAP}),
        ({"bad": "tags"}, {"delegations": {"bad": "tags"}}),
        ({}, {"delegations": {}}),
        (None, {"delegations": None}),  # API returns None on exceptions
    ],
)
def test_get_signatures(targets_map, expected, client):
    with patch("endpoints.api.signing.tuf_metadata_api") as mock_tuf:
        mock_tuf.get_all_tags_with_expiration.return_value = targets_map
        with client_with_identity("devtable", client) as cl:
            params = {"repository": "devtable/trusted"}
            assert tags_equal(
                expected, conduct_api_call(cl, RepositorySignatures, "GET", params, None, 200).json
            )
