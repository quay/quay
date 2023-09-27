from test.fixtures import *

import pytest, json

from data.model.autoprune import *
from data.model.user import get_user
from data.model import InvalidUsernameException, NamespacePolicyAlreadyExists
from data.model.organization import create_organization


ORG1_NAME = "org1"
ORG2_NAME = "org2"
ORG3_NAME = "org3"


class TestNameSpaceAutoprune:
    @pytest.fixture(autouse=True)
    def setup(self, initialized_db):
        user = get_user("devtable")
        self.org1 = create_organization(ORG1_NAME, f"{ORG1_NAME}@devtable.com", user)
        self.org2 = create_organization(ORG2_NAME, f"{ORG2_NAME}@devtable.com", user)
        self.org3 = create_organization(ORG3_NAME, f"{ORG3_NAME}@devtable.com", user)
        self.number_of_tags_policy = {"method": "number_of_tags", "value": 10}
        self.namespace_policy = create_namespace_autoprune_policy(
            ORG3_NAME, self.number_of_tags_policy, create_task=False
        )

    def test_policy_creation_without_task(self):
        # policy based on tag count
        new_policy1 = create_namespace_autoprune_policy(
            ORG1_NAME, self.number_of_tags_policy, create_task=False
        )
        assert new_policy1.namespace.id == self.org1.id
        assert json.loads(new_policy1.policy) == self.number_of_tags_policy

        # policy based on tag creation date
        create_date_policy = {"method": "creation_date", "value": 1695668761}
        new_policy2 = create_namespace_autoprune_policy(
            ORG2_NAME, create_date_policy, create_task=False
        )
        assert new_policy2.namespace.id == self.org2.id
        assert json.loads(new_policy2.policy) == create_date_policy

    def test_policy_creation_with_task(self):
        new_policy = create_namespace_autoprune_policy(
            ORG1_NAME, self.number_of_tags_policy, create_task=True
        )
        assert new_policy.namespace.id == self.org1.id
        assert namespace_has_autoprune_task(self.org1.id) is True

    def test_policy_creation_with_incorrect_org(self):
        with pytest.raises(InvalidUsernameException) as excerror:
            create_namespace_autoprune_policy(
                "non-existant org", self.number_of_tags_policy, create_task=True
            )
        assert str(excerror.value) == "Invalid namespace provided: non-existant org"

    def test_policy_creation_for_org_with_policy(self):
        create_namespace_autoprune_policy(ORG1_NAME, self.number_of_tags_policy, create_task=False)
        with pytest.raises(NamespacePolicyAlreadyExists) as excerror:
            create_namespace_autoprune_policy(
                ORG1_NAME, self.number_of_tags_policy, create_task=True
            )
        assert (
            str(excerror.value)
            == "Policy for this namespace already exists, delete existing to create new policy"
        )

    def test_get_policies_by_orgname(self):
        org_policies = get_namespace_autoprune_policies_by_orgname(ORG3_NAME)
        assert len(org_policies) == 1
        assert org_policies[0]._db_row.namespace_id == self.org3.id

        org2_policies = get_namespace_autoprune_policies_by_orgname(ORG2_NAME)
        assert len(org2_policies) == 0

    def test_get_policies_by_namespace_id(self):
        org_policies = get_namespace_autoprune_policies_by_id(self.org3.id)
        assert len(org_policies) == 1
        assert org_policies[0]._db_row.namespace_id == self.org3.id

        org2_policies = get_namespace_autoprune_policies_by_orgname(ORG2_NAME)
        assert len(org2_policies) == 0

    def test_update_policy(self):
        new_policy_config = {"method": "number_of_tags", "value": 100}
        updated = update_namespace_autoprune_policy(
            ORG3_NAME, self.namespace_policy.uuid, new_policy_config
        )
        assert updated is True

        policies = get_namespace_autoprune_policies_by_orgname(ORG3_NAME)
        assert policies[0].config == new_policy_config

    def test_incorrect_update_policy(self):
        with pytest.raises(NamespaceAutoPrunePolicyTable.DoesNotExist) as excerror:
            update_namespace_autoprune_policy(ORG3_NAME, "random-uuid", {})
        assert (
            str(excerror.value)
            == f"Policy not found for namespace: {ORG3_NAME} with uuid: random-uuid"
        )

        with pytest.raises(InvalidUsernameException) as excerror:
            update_namespace_autoprune_policy("randome", "random-uuid", {})
        assert str(excerror.value) == f"Invalid namespace provided: randome"

    def test_delete_policy(self):
        deleted = delete_namespace_autoprune_policy(ORG3_NAME, self.namespace_policy.uuid)
        assert deleted is True

    def test_incorrect_delete_policy(self):
        # incorrect orgname
        with pytest.raises(InvalidUsernameException) as excerror:
            delete_namespace_autoprune_policy("randome", "random-uuid")
        assert str(excerror.value) == f"Invalid namespace provided: randome"

        # incorrect uuid
        with pytest.raises(NamespaceAutoPrunePolicyTable.DoesNotExist) as excerror:
            delete_namespace_autoprune_policy(ORG3_NAME, "random-uuid")
        assert (
            str(excerror.value)
            == f"Policy not found for namespace: {ORG3_NAME} with uuid: random-uuid"
        )

    def test_namespace_policy(self):
        policy_exists = namespace_has_autoprune_policy(self.org3.id)
        assert policy_exists is True
        namespace_policy = get_namespace_autoprune_policy(
            self.org3.username, self.namespace_policy.uuid
        )
        assert namespace_policy.uuid == self.namespace_policy.uuid
        assert namespace_policy._db_row.namespace_id == self.org3.id

        # incorrect params
        policy_exists = namespace_has_autoprune_policy("randome")
        assert policy_exists is False
        resp = get_namespace_autoprune_policy("randome", "randome-uuid")
        assert resp is None

    def test_valid_method(self):
        assert valid_value(AutoPruneMethod.NUMBER_OF_TAGS, 10) is True
        assert valid_value(AutoPruneMethod.NUMBER_OF_TAGS, -1) is False
        assert valid_value(AutoPruneMethod.NUMBER_OF_TAGS, 0) is False
        assert valid_value(AutoPruneMethod.NUMBER_OF_TAGS, "1") is False
        assert valid_value(AutoPruneMethod.NUMBER_OF_TAGS, 1.5) is False
        assert valid_value(AutoPruneMethod.NUMBER_OF_TAGS, "randome string") is False
        assert valid_value(AutoPruneMethod.NUMBER_OF_TAGS, None) is False

        assert valid_value(AutoPruneMethod.CREATION_DATE, "2d") is True
        assert valid_value(AutoPruneMethod.CREATION_DATE, "") is False
        assert valid_value(AutoPruneMethod.CREATION_DATE, 123) is False
        assert valid_value(AutoPruneMethod.CREATION_DATE, "randome") is False

        assert valid_value("randome method", "randome") is False
        assert valid_value("randome method", None) is False
