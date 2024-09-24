import json

import pytest

from data.model.autoprune import *
from data.model.organization import create_organization
from data.model.repository import create_repository, set_repository_state
from data.model.user import get_user
from test.fixtures import *

ORG1_NAME = "org1"
ORG2_NAME = "org2"
ORG3_NAME = "org3"
REPO1_NAME = "repo1"
REPO2_NAME = "repo2"
REPO3_NAME = "repo3"


class TestRepositoryAutoprune:
    @pytest.fixture(autouse=True)
    def setup(self, initialized_db):
        user = get_user("devtable")
        self.org1 = create_organization(ORG1_NAME, f"{ORG1_NAME}@devtable.com", user)
        self.org2 = create_organization(ORG2_NAME, f"{ORG2_NAME}@devtable.com", user)
        self.org3 = create_organization(ORG3_NAME, f"{ORG3_NAME}@devtable.com", user)
        self.number_of_tags_policy = {"method": "number_of_tags", "value": 10}

        self.repo1 = create_repository(ORG1_NAME, REPO1_NAME, None)
        set_repository_state(self.repo1, RepositoryState.NORMAL)

        self.repo2 = create_repository(ORG2_NAME, REPO2_NAME, None)
        set_repository_state(self.repo2, RepositoryState.NORMAL)

        self.repo3 = create_repository(ORG3_NAME, REPO3_NAME, None)
        set_repository_state(self.repo3, RepositoryState.NORMAL)

        self.repository_policy3 = create_repository_autoprune_policy(
            ORG3_NAME, REPO3_NAME, self.number_of_tags_policy, create_task=False
        )

    def test_repo_policy_creation_without_task(self):
        # policy based on tag count
        new_repo_policy1 = create_repository_autoprune_policy(
            ORG1_NAME, REPO1_NAME, self.number_of_tags_policy, create_task=False
        )
        assert new_repo_policy1.namespace.id == self.org1.id
        assert new_repo_policy1.repository.id == self.repo1.id
        assert json.loads(new_repo_policy1.policy) == self.number_of_tags_policy

        # policy based on tag creation date
        create_date_policy = {"method": "creation_date", "value": "7d"}
        new_repo_policy2 = create_repository_autoprune_policy(
            ORG2_NAME, REPO2_NAME, create_date_policy, create_task=False
        )
        assert new_repo_policy2.namespace.id == self.org2.id
        assert new_repo_policy2.repository.id == self.repo2.id
        assert json.loads(new_repo_policy2.policy) == create_date_policy

    def test_repo_policy_creation_with_task(self):
        new_repo_policy = create_repository_autoprune_policy(
            ORG1_NAME, REPO1_NAME, self.number_of_tags_policy, create_task=True
        )
        assert new_repo_policy.namespace.id == self.org1.id
        assert new_repo_policy.repository.id == self.repo1.id
        assert namespace_has_autoprune_task(self.org1.id) is True

    def test_repo_policy_creation_with_incorrect_repo_name(self):
        with pytest.raises(InvalidRepositoryException) as excerror:
            create_repository_autoprune_policy(
                ORG1_NAME, "nonexistentrepo", self.number_of_tags_policy, create_task=True
            )
        assert str(excerror.value) == "Repository does not exist: nonexistentrepo"

    def test_duplicate_repo_policy_creation_for_repo_with_policy(self):
        with pytest.raises(RepositoryAutoPrunePolicyAlreadyExists) as excerror:
            create_repository_autoprune_policy(
                ORG3_NAME, REPO3_NAME, self.number_of_tags_policy, create_task=True
            )
        assert (
            str(excerror.value)
            == "Existing policy with same values for this repository, duplicate policies are not permitted"
        )

    def test_get_repo_policies_by_reponame(self):
        repo_policies = get_repository_autoprune_policies_by_repo_name(ORG3_NAME, REPO3_NAME)
        assert len(repo_policies) == 1
        assert repo_policies[0]._db_row.namespace_id == self.org3.id
        assert repo_policies[0].repository_id == self.repo3.id

        repo2_policies = get_repository_autoprune_policies_by_repo_name(ORG2_NAME, REPO2_NAME)
        assert len(repo2_policies) == 0

    def test_get_repo_policies_by_namespace_id(self):
        repo_policies = get_repository_autoprune_policies_by_namespace_id(self.org3.id)
        assert len(repo_policies) == 1
        assert repo_policies[0]._db_row.namespace_id == self.org3.id
        assert repo_policies[0].repository_id == self.repo3.id

        repo2_policies = get_repository_autoprune_policies_by_namespace_id(self.org2.id)
        assert len(repo2_policies) == 0

    def test_get_repo_policies_by_repo_id(self):
        repo_policies = get_repository_autoprune_policies_by_repo_id(self.repo3.id)
        assert len(repo_policies) == 1
        assert repo_policies[0]._db_row.namespace_id == self.org3.id
        assert repo_policies[0].repository_id == self.repo3.id

        repo2_policies = get_repository_autoprune_policies_by_repo_id(self.repo2.id)
        assert len(repo2_policies) == 0

    def test_update_repo_policy(self):
        new_policy_config = {"method": "number_of_tags", "value": 100}
        updated = update_repository_autoprune_policy(
            ORG3_NAME, REPO3_NAME, self.repository_policy3.uuid, new_policy_config
        )
        assert updated is True

        repo_policies = get_repository_autoprune_policies_by_repo_name(ORG3_NAME, REPO3_NAME)
        assert repo_policies[0].config == new_policy_config

    def test_incorrect_update_repo_policy(self):
        # incorrect uuid
        with pytest.raises(RepositoryAutoPrunePolicyDoesNotExist) as excerror:
            update_repository_autoprune_policy(ORG3_NAME, REPO3_NAME, "random-uuid", {})
        assert (
            str(excerror.value)
            == f"Policy not found for repository: {REPO3_NAME} with uuid: random-uuid"
        )

        # incorrect reponame
        with pytest.raises(InvalidRepositoryException) as excerror:
            update_repository_autoprune_policy(
                ORG3_NAME, "nonexistentrepo", self.repository_policy3.uuid, {}
            )
        assert str(excerror.value) == "Repository does not exist: nonexistentrepo"

    def test_delete_repo_policy(self):
        deleted = delete_repository_autoprune_policy(
            ORG3_NAME, REPO3_NAME, self.repository_policy3.uuid
        )
        assert deleted is True

    def test_incorrect_delete_repo_policy(self):
        # incorrect uuid
        with pytest.raises(RepositoryAutoPrunePolicyDoesNotExist) as excerror:
            delete_repository_autoprune_policy(ORG3_NAME, REPO3_NAME, "random-uuid")
        assert (
            str(excerror.value)
            == f"Policy not found for repository: {REPO3_NAME} with uuid: random-uuid"
        )

        # incorrect reponame
        with pytest.raises(InvalidRepositoryException) as excerror:
            delete_repository_autoprune_policy(
                ORG3_NAME, "nonexistentrepo", self.repository_policy3.uuid
            )
        assert str(excerror.value) == "Repository does not exist: nonexistentrepo"

    def test_repository_policy(self):
        policy_exists = repository_has_autoprune_policy(self.repo3.id)
        assert policy_exists is True
        repository_policy = get_repository_autoprune_policy_by_uuid(
            self.repo3.name, self.repository_policy3.uuid
        )
        assert repository_policy.uuid == self.repository_policy3.uuid
        assert repository_policy.repository_id == self.repo3.id

        resp = get_repository_autoprune_policy_by_uuid("nonexistentrepo", "randome-uuid")
        assert resp is None
