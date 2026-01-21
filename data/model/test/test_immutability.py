import pytest

from data.model import (
    DuplicateImmutabilityPolicy,
    ImmutabilityPolicyDoesNotExist,
    InvalidImmutabilityPolicy,
)
from data.model.immutability import (
    _matches_policy,
    _validate_policy,
    create_namespace_immutability_policy,
    create_repository_immutability_policy,
    delete_namespace_immutability_policy,
    delete_repository_immutability_policy,
    evaluate_immutability_policies,
    get_namespace_immutability_policies,
    get_namespace_immutability_policy,
    get_repository_immutability_policies,
    get_repository_immutability_policy,
    update_namespace_immutability_policy,
    update_repository_immutability_policy,
)
from data.model.organization import create_organization
from data.model.repository import create_repository
from data.model.user import create_user_noverify
from test.fixtures import *  # noqa: F401, F403


def create_org(user_name, user_email, org_name, org_email):
    user_obj = create_user_noverify(user_name, user_email)
    return create_organization(org_name, org_email, user_obj)


class TestValidation:
    def test_valid_policy(self):
        _validate_policy({"tag_pattern": "^v[0-9]+\\.[0-9]+\\.[0-9]+$"})

    def test_valid_policy_with_tag_pattern_matches(self):
        _validate_policy({"tag_pattern": "^latest$", "tag_pattern_matches": True})
        _validate_policy({"tag_pattern": "^dev-.*$", "tag_pattern_matches": False})

    def test_missing_tag_pattern(self):
        with pytest.raises(InvalidImmutabilityPolicy):
            _validate_policy({})

    def test_empty_tag_pattern(self):
        with pytest.raises(InvalidImmutabilityPolicy):
            _validate_policy({"tag_pattern": ""})

    def test_invalid_regex(self):
        with pytest.raises(InvalidImmutabilityPolicy):
            _validate_policy({"tag_pattern": "[invalid"})

    def test_invalid_tag_pattern_matches_type(self):
        with pytest.raises(InvalidImmutabilityPolicy):
            _validate_policy({"tag_pattern": "^v.*$", "tag_pattern_matches": "yes"})

    def test_pattern_too_long(self):
        with pytest.raises(InvalidImmutabilityPolicy):
            _validate_policy({"tag_pattern": "a" * 257})

    def test_pattern_at_max_length(self):
        _validate_policy({"tag_pattern": "a" * 256})


class TestMatchesPolicy:
    def test_matches_semver(self):
        assert _matches_policy("v1.2.3", "^v[0-9]+\\.[0-9]+\\.[0-9]+$", True) is True
        assert _matches_policy("latest", "^v[0-9]+\\.[0-9]+\\.[0-9]+$", True) is False

    def test_inverted_match(self):
        # tag_pattern_matches=False: non-matching tags become immutable
        assert _matches_policy("dev-branch", "^dev-.*$", False) is False
        assert _matches_policy("v1.0.0", "^dev-.*$", False) is True


class TestNamespacePolicyCRUD:
    def test_create_and_get(self, initialized_db):
        org = create_org("testuser", "test@example.com", "testorg", "org@example.com")

        policy = create_namespace_immutability_policy(org.username, {"tag_pattern": "^v.*$"})
        assert policy.uuid is not None

        policies = get_namespace_immutability_policies(org.username)
        assert len(policies) == 1
        assert policies[0].tag_pattern == "^v.*$"

    def test_get_by_uuid(self, initialized_db):
        org = create_org("testuser2", "test2@example.com", "testorg2", "org2@example.com")

        created = create_namespace_immutability_policy(org.username, {"tag_pattern": "^latest$"})
        policy = get_namespace_immutability_policy(org.username, created.uuid)

        assert policy is not None
        assert policy.uuid == created.uuid

    def test_update(self, initialized_db):
        org = create_org("testuser3", "test3@example.com", "testorg3", "org3@example.com")

        created = create_namespace_immutability_policy(org.username, {"tag_pattern": "^v1.*$"})
        update_namespace_immutability_policy(org.username, created.uuid, {"tag_pattern": "^v2.*$"})

        updated = get_namespace_immutability_policy(org.username, created.uuid)
        assert updated.tag_pattern == "^v2.*$"

    def test_delete(self, initialized_db):
        org = create_org("testuser4", "test4@example.com", "testorg4", "org4@example.com")

        created = create_namespace_immutability_policy(org.username, {"tag_pattern": "^v.*$"})
        delete_namespace_immutability_policy(org.username, created.uuid)

        assert get_namespace_immutability_policy(org.username, created.uuid) is None

    def test_delete_nonexistent_raises(self, initialized_db):
        org = create_org("testuser5", "test5@example.com", "testorg5", "org5@example.com")

        with pytest.raises(ImmutabilityPolicyDoesNotExist):
            delete_namespace_immutability_policy(org.username, "nonexistent")

    def test_update_nonexistent_raises(self, initialized_db):
        org = create_org("testuser6", "test6@example.com", "testorg6", "org6@example.com")

        with pytest.raises(ImmutabilityPolicyDoesNotExist):
            update_namespace_immutability_policy(
                org.username, "nonexistent", {"tag_pattern": "^v.*$"}
            )

    def test_duplicate_policy_raises(self, initialized_db):
        org = create_org("testuser7", "test7@example.com", "testorg7", "org7@example.com")

        create_namespace_immutability_policy(org.username, {"tag_pattern": "^v.*$"})

        with pytest.raises(DuplicateImmutabilityPolicy):
            create_namespace_immutability_policy(org.username, {"tag_pattern": "^v.*$"})

    def test_different_pattern_allowed(self, initialized_db):
        org = create_org("testuser8", "test8@example.com", "testorg8", "org8@example.com")

        create_namespace_immutability_policy(org.username, {"tag_pattern": "^v.*$"})
        create_namespace_immutability_policy(org.username, {"tag_pattern": "^release-.*$"})

        policies = get_namespace_immutability_policies(org.username)
        assert len(policies) == 2

    def test_same_pattern_different_matches_allowed(self, initialized_db):
        org = create_org("testuser9", "test9@example.com", "testorg9", "org9@example.com")

        create_namespace_immutability_policy(
            org.username, {"tag_pattern": "^dev-.*$", "tag_pattern_matches": True}
        )
        create_namespace_immutability_policy(
            org.username, {"tag_pattern": "^dev-.*$", "tag_pattern_matches": False}
        )

        policies = get_namespace_immutability_policies(org.username)
        assert len(policies) == 2


class TestRepositoryPolicyCRUD:
    def test_create_and_get(self, initialized_db):
        org = create_org("repouser", "repo@example.com", "repoorg", "repoorg@example.com")
        repo = create_repository(org.username, "testrepo", None)

        policy = create_repository_immutability_policy(
            org.username, repo.name, {"tag_pattern": "^release-.*$"}
        )
        assert policy.uuid is not None

        policies = get_repository_immutability_policies(org.username, repo.name)
        assert len(policies) == 1

    def test_update(self, initialized_db):
        org = create_org("repouser2", "repo2@example.com", "repoorg2", "repoorg2@example.com")
        repo = create_repository(org.username, "testrepo2", None)

        created = create_repository_immutability_policy(
            org.username, repo.name, {"tag_pattern": "^v1.*$"}
        )
        update_repository_immutability_policy(
            org.username, repo.name, created.uuid, {"tag_pattern": "^v2.*$"}
        )

        updated = get_repository_immutability_policy(org.username, repo.name, created.uuid)
        assert updated.tag_pattern == "^v2.*$"

    def test_delete(self, initialized_db):
        org = create_org("repouser3", "repo3@example.com", "repoorg3", "repoorg3@example.com")
        repo = create_repository(org.username, "testrepo3", None)

        created = create_repository_immutability_policy(
            org.username, repo.name, {"tag_pattern": "^v.*$"}
        )
        delete_repository_immutability_policy(org.username, repo.name, created.uuid)

        assert get_repository_immutability_policy(org.username, repo.name, created.uuid) is None

    def test_duplicate_policy_raises(self, initialized_db):
        org = create_org("repouser4", "repo4@example.com", "repoorg4", "repoorg4@example.com")
        repo = create_repository(org.username, "testrepo4", None)

        create_repository_immutability_policy(org.username, repo.name, {"tag_pattern": "^v.*$"})

        with pytest.raises(DuplicateImmutabilityPolicy):
            create_repository_immutability_policy(org.username, repo.name, {"tag_pattern": "^v.*$"})


class TestEvaluatePolicies:
    def test_no_policies(self, initialized_db):
        org = create_org("evaluser", "eval@example.com", "evalorg", "evalorg@example.com")
        repo = create_repository(org.username, "evalrepo", None)

        assert evaluate_immutability_policies(repo.id, org.id, "v1.0.0") is False

    def test_matching_namespace_policy(self, initialized_db):
        org = create_org("evaluser2", "eval2@example.com", "evalorg2", "evalorg2@example.com")
        repo = create_repository(org.username, "evalrepo2", None)

        create_namespace_immutability_policy(org.username, {"tag_pattern": "^v[0-9]+.*$"})

        assert evaluate_immutability_policies(repo.id, org.id, "v1.0.0") is True
        assert evaluate_immutability_policies(repo.id, org.id, "latest") is False

    def test_matching_repository_policy(self, initialized_db):
        org = create_org("evaluser3", "eval3@example.com", "evalorg3", "evalorg3@example.com")
        repo = create_repository(org.username, "evalrepo3", None)

        create_repository_immutability_policy(
            org.username, repo.name, {"tag_pattern": "^release-.*$"}
        )

        assert evaluate_immutability_policies(repo.id, org.id, "release-1.0") is True
        assert evaluate_immutability_policies(repo.id, org.id, "dev-branch") is False

    def test_inverted_match(self, initialized_db):
        org = create_org("evaluser4", "eval4@example.com", "evalorg4", "evalorg4@example.com")
        repo = create_repository(org.username, "evalrepo4", None)

        # Make all tags EXCEPT dev-* immutable
        create_namespace_immutability_policy(
            org.username, {"tag_pattern": "^dev-.*$", "tag_pattern_matches": False}
        )

        assert evaluate_immutability_policies(repo.id, org.id, "dev-branch") is False
        assert evaluate_immutability_policies(repo.id, org.id, "v1.0.0") is True


class TestGetView:
    def test_namespace_policy_view(self, initialized_db):
        org = create_org("viewuser", "view@example.com", "vieworg", "vieworg@example.com")

        created = create_namespace_immutability_policy(
            org.username, {"tag_pattern": "^v.*$", "tag_pattern_matches": True}
        )
        policy = get_namespace_immutability_policy(org.username, created.uuid)

        view = policy.get_view()
        assert view["uuid"] == created.uuid
        assert view["tagPattern"] == "^v.*$"
        assert view["tagPatternMatches"] is True
