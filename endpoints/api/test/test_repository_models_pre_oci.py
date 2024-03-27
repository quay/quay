import pytest
from mock import ANY, MagicMock, patch

from data.database import QuotaRepositorySize
from data.model.repository import get_repository
from endpoints.api.repository import Repository, RepositoryList, RepositoryTrust
from endpoints.api.repository_models_interface import RepositoryBaseElement
from endpoints.api.repository_models_pre_oci import pre_oci_model
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from features import FeatureNameValue
from test.fixtures import *


def test_add_quota_view(initialized_db):
    repo_with_no_size_row = get_repo_base_element("randomuser", "randomrepo")
    repos = [
        get_repo_base_element("buynlarge", "orgrepo"),
        get_repo_base_element("devtable", "simple"),
        repo_with_no_size_row,
        get_repo_base_element("devtable", "building"),
    ]

    QuotaRepositorySize.delete().where(
        QuotaRepositorySize.repository == repo_with_no_size_row.id
    ).execute()
    assert (
        QuotaRepositorySize.select()
        .where(QuotaRepositorySize.repository == repo_with_no_size_row.id)
        .count()
        == 0
    )

    repos_with_view = pre_oci_model.add_quota_view(repos)

    assert repos_with_view[0].get("quota_report").get("quota_bytes") == 92
    assert repos_with_view[0].get("quota_report").get("configured_quota") == 3000

    assert repos_with_view[1].get("quota_report").get("quota_bytes") == 92
    assert repos_with_view[1].get("quota_report").get("configured_quota") is None

    assert repos_with_view[2].get("quota_report").get("quota_bytes") == 0
    assert repos_with_view[2].get("quota_report").get("configured_quota") == 6000

    assert repos_with_view[3].get("quota_report").get("quota_bytes") == 0
    assert repos_with_view[3].get("quota_report").get("configured_quota") is None


def get_repo_base_element(namespace, repo):
    repo = get_repository(namespace, repo)
    return RepositoryBaseElement(
        repo.id,
        repo.namespace_user.username,
        repo.name,
        False,
        False,
        "",
        repo.description,
        repo.namespace_user.organization,
        repo.namespace_user.removed_tag_expiration_s,
        None,
        None,
        False,
        False,
        False,
        repo.namespace_user.stripe_id is None,
        repo.state,
    )
