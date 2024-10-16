from unittest.mock import MagicMock, patch

import pytest

from data import model
from data.model.autoprune import (
    NamespaceAutoPrunePolicy,
    RepositoryAutoPrunePolicy,
    execute_policies_for_repo,
)
from data.model.user import get_user
from test.fixtures import *


@pytest.mark.parametrize(
    "expected_policy_calls, include_repo_policies",
    [
        (
            [
                {"method": "creation_date", "value": "2d"},
                {"method": "number_of_tags", "value": "10"},
            ],
            True,
        ),
        ([{"method": "creation_date", "value": "2d"}], False),
    ],
)
def test_execute_policies_for_repo(initialized_db, expected_policy_calls, include_repo_policies):
    repository = model.repository.get_repository("devtable", "simple")
    namespace = get_user("devtable")
    ns_policies = [NamespaceAutoPrunePolicy(policy_dict={"method": "creation_date", "value": "2d"})]
    with patch(
        "data.model.autoprune.get_repository_autoprune_policies_by_repo_id",
        MagicMock(
            return_value=[
                RepositoryAutoPrunePolicy(policy_dict={"method": "number_of_tags", "value": "10"})
            ]
        ),
    ):
        with patch(
            "data.model.autoprune.execute_policy_on_repo", MagicMock()
        ) as mock_execute_policy_on_repo:

            def assert_mock_mock_execute_policy_on_repo(
                policy, repo_id, namespace_id, tag_page_limit
            ):
                expected_call = expected_policy_calls.pop(0)
                assert policy.config == expected_call
                assert repo_id == repository.id
                assert namespace_id == namespace.id
                assert tag_page_limit == 100

            mock_execute_policy_on_repo.side_effect = assert_mock_mock_execute_policy_on_repo

            execute_policies_for_repo(
                ns_policies, repository, namespace.id, include_repo_policies=include_repo_policies
            )
            assert len(expected_policy_calls) == 0
