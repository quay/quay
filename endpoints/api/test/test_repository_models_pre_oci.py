from endpoints.api.repository_models_pre_oci import pre_oci_model
from test.fixtures import *

import pytest
from mock import ANY, MagicMock, patch

from data import database, model
from endpoints.api.repository import Repository, RepositoryList, RepositoryTrust
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from features import FeatureNameValue


def test_add_quota_view(initialized_db):
    repos = [
        {
            "namespace": "buynlarge",
            "name": "orgrepo",
        },
        {
            "namespace": "devtable",
            "name": "simple",
        },
        {
            "namespace": "devtable",
            "name": None,
        },
        {
            "namespace": "buynlarge",
            "name": "doesnotexist",
        },
    ]

    pre_oci_model.add_quota_view(repos)

    assert repos[0].get("quota_report").get("quota_bytes") == 92
    assert repos[0].get("quota_report").get("configured_quota") == 3000

    assert repos[1].get("quota_report").get("quota_bytes") == 92
    assert repos[1].get("quota_report").get("configured_quota") is None

    assert repos[2].get("quota_report") is None

    assert repos[3].get("quota_report") is None
