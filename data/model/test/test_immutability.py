from unittest.mock import patch

import pytest

from data.database import Tag, get_epoch_timestamp_ms
from data.model import (
    DuplicateImmutabilityPolicy,
    ImmutabilityPolicyDoesNotExist,
    InvalidImmutabilityPolicy,
)
from data.model.immutability import (
    _matches_policy,
    _validate_policy,
    apply_immutability_policy_to_existing_tags,
    create_namespace_immutability_policy,
    create_repository_immutability_policy,
    delete_namespace_immutability_policy,
    delete_repository_immutability_policy,
    evaluate_immutability_policies,
    get_namespace_immutability_policies,
    get_namespace_immutability_policy,
    get_repository_immutability_policies,
    get_repository_immutability_policy,
    namespace_has_immutable_tags,
    update_namespace_immutability_policy,
    update_repository_immutability_policy,
)
from data.model.oci.tag import filter_to_alive_tags
from data.model.organization import create_organization
from data.model.repository import create_repository, get_repository
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


def _create_tag(repository, manifest, name, immutable=False, hidden=False, expired=False):
    """Helper to create a tag for testing."""
    now_ms = get_epoch_timestamp_ms()
    lifetime_end_ms = now_ms - 1000 if expired else None
    return Tag.create(
        name=name,
        repository=repository.id,
        manifest=manifest,
        lifetime_start_ms=now_ms - 10000,
        lifetime_end_ms=lifetime_end_ms,
        hidden=hidden,
        immutable=immutable,
        reversion=False,
        tag_kind=Tag.tag_kind.get_id("tag"),
    )


def _get_manifest_from_repo(repo):
    """Get an existing manifest from a repository's alive tags."""
    for tag in filter_to_alive_tags(Tag.select().where(Tag.repository == repo.id)):
        if tag.manifest:
            return tag.manifest
    return None


class TestRetroactiveImmutability:
    def test_namespace_policy_marks_matching_tags(self, initialized_db):
        """Verify v* tags become immutable when namespace policy is created."""
        org = create_org("retrouser1", "retro1@example.com", "retroorg1", "retroorg1@example.com")
        repo = create_repository(org.username, "retrorepo1", None)

        # Get a manifest from an existing repo to use
        existing_repo = get_repository("devtable", "simple")
        manifest = _get_manifest_from_repo(existing_repo)
        assert manifest is not None

        # Create tags before policy
        tag_v1 = _create_tag(repo, manifest, "v1.0.0")
        tag_v2 = _create_tag(repo, manifest, "v2.0.0")
        tag_latest = _create_tag(repo, manifest, "notversioned")

        # Verify tags are not immutable
        assert Tag.get(Tag.id == tag_v1.id).immutable is False
        assert Tag.get(Tag.id == tag_v2.id).immutable is False
        assert Tag.get(Tag.id == tag_latest.id).immutable is False

        # Create policy matching v* tags
        create_namespace_immutability_policy(org.username, {"tag_pattern": "^v.*$"})

        # Verify v* tags are now immutable, notversioned is not
        assert Tag.get(Tag.id == tag_v1.id).immutable is True
        assert Tag.get(Tag.id == tag_v2.id).immutable is True
        assert Tag.get(Tag.id == tag_latest.id).immutable is False

    def test_repository_policy_marks_matching_tags(self, initialized_db):
        """Verify repo-scoped enforcement works."""
        org = create_org("retrouser2", "retro2@example.com", "retroorg2", "retroorg2@example.com")
        repo = create_repository(org.username, "retrorepo2", None)

        existing_repo = get_repository("devtable", "simple")
        manifest = _get_manifest_from_repo(existing_repo)

        tag_release = _create_tag(repo, manifest, "release-1.0")
        tag_dev = _create_tag(repo, manifest, "dev-branch")

        create_repository_immutability_policy(
            org.username, repo.name, {"tag_pattern": "^release-.*$"}
        )

        assert Tag.get(Tag.id == tag_release.id).immutable is True
        assert Tag.get(Tag.id == tag_dev.id).immutable is False

    def test_inverted_pattern_marks_non_matching_tags(self, initialized_db):
        """Verify tag_pattern_matches=False marks non-matching tags."""
        org = create_org("retrouser3", "retro3@example.com", "retroorg3", "retroorg3@example.com")
        repo = create_repository(org.username, "retrorepo3", None)

        existing_repo = get_repository("devtable", "simple")
        manifest = _get_manifest_from_repo(existing_repo)

        tag_dev = _create_tag(repo, manifest, "dev-branch")
        tag_v1 = _create_tag(repo, manifest, "v1.0.0")

        # Make all tags EXCEPT dev-* immutable
        create_namespace_immutability_policy(
            org.username, {"tag_pattern": "^dev-.*$", "tag_pattern_matches": False}
        )

        # dev-* should NOT be immutable, everything else should be
        assert Tag.get(Tag.id == tag_dev.id).immutable is False
        assert Tag.get(Tag.id == tag_v1.id).immutable is True

    def test_update_policy_marks_newly_matching_tags(self, initialized_db):
        """Verify pattern change marks new matches."""
        org = create_org("retrouser4", "retro4@example.com", "retroorg4", "retroorg4@example.com")
        repo = create_repository(org.username, "retrorepo4", None)

        existing_repo = get_repository("devtable", "simple")
        manifest = _get_manifest_from_repo(existing_repo)

        tag_v1 = _create_tag(repo, manifest, "v1.0.0")
        tag_release = _create_tag(repo, manifest, "release-1.0")

        # Create policy matching v* tags
        policy = create_namespace_immutability_policy(org.username, {"tag_pattern": "^v.*$"})

        assert Tag.get(Tag.id == tag_v1.id).immutable is True
        assert Tag.get(Tag.id == tag_release.id).immutable is False

        # Update policy to match release-* instead
        update_namespace_immutability_policy(
            org.username, policy.uuid, {"tag_pattern": "^release-.*$"}
        )

        # v1 should still be immutable (we don't unmark)
        # release should now be immutable
        assert Tag.get(Tag.id == tag_v1.id).immutable is True
        assert Tag.get(Tag.id == tag_release.id).immutable is True

    def test_delete_policy_does_not_unmark_tags(self, initialized_db):
        """Verify immutability persists after policy delete."""
        org = create_org("retrouser5", "retro5@example.com", "retroorg5", "retroorg5@example.com")
        repo = create_repository(org.username, "retrorepo5", None)

        existing_repo = get_repository("devtable", "simple")
        manifest = _get_manifest_from_repo(existing_repo)

        tag_v1 = _create_tag(repo, manifest, "v1.0.0")

        policy = create_namespace_immutability_policy(org.username, {"tag_pattern": "^v.*$"})

        assert Tag.get(Tag.id == tag_v1.id).immutable is True

        # Delete the policy
        delete_namespace_immutability_policy(org.username, policy.uuid)

        # Tag should still be immutable
        assert Tag.get(Tag.id == tag_v1.id).immutable is True

    def test_already_immutable_tags_not_updated_again(self, initialized_db):
        """Verify idempotency - already immutable tags aren't touched."""
        org = create_org("retrouser6", "retro6@example.com", "retroorg6", "retroorg6@example.com")
        repo = create_repository(org.username, "retrorepo6", None)

        existing_repo = get_repository("devtable", "simple")
        manifest = _get_manifest_from_repo(existing_repo)

        # Create an already immutable tag
        tag_v1 = _create_tag(repo, manifest, "v1.0.0", immutable=True)

        # Create policy - should not fail or double-update
        create_namespace_immutability_policy(org.username, {"tag_pattern": "^v.*$"})

        # Tag should still be immutable
        assert Tag.get(Tag.id == tag_v1.id).immutable is True

    def test_batch_processing_large_number_of_tags(self, initialized_db):
        """Test pagination with small batch."""
        org = create_org("retrouser7", "retro7@example.com", "retroorg7", "retroorg7@example.com")
        repo = create_repository(org.username, "retrorepo7", None)

        existing_repo = get_repository("devtable", "simple")
        manifest = _get_manifest_from_repo(existing_repo)

        # Create more tags than a small batch size
        tag_ids = []
        for i in range(10):
            tag = _create_tag(repo, manifest, f"v{i}.0.0")
            tag_ids.append(tag.id)

        # Apply policy with small batch size
        marked = apply_immutability_policy_to_existing_tags(
            namespace_id=org.id,
            repository_id=repo.id,
            tag_pattern="^v.*$",
            tag_pattern_matches=True,
            batch_size=3,  # Small batch to test pagination
        )

        assert marked == 10

        # Verify all tags are immutable
        for tag_id in tag_ids:
            assert Tag.get(Tag.id == tag_id).immutable is True

    def test_namespace_policy_affects_multiple_repositories(self, initialized_db):
        """Cross-repo enforcement for namespace policies."""
        org = create_org("retrouser8", "retro8@example.com", "retroorg8", "retroorg8@example.com")
        repo1 = create_repository(org.username, "retrorepo8a", None)
        repo2 = create_repository(org.username, "retrorepo8b", None)

        existing_repo = get_repository("devtable", "simple")
        manifest = _get_manifest_from_repo(existing_repo)

        tag1 = _create_tag(repo1, manifest, "v1.0.0")
        tag2 = _create_tag(repo2, manifest, "v2.0.0")

        create_namespace_immutability_policy(org.username, {"tag_pattern": "^v.*$"})

        # Both tags in different repos should be immutable
        assert Tag.get(Tag.id == tag1.id).immutable is True
        assert Tag.get(Tag.id == tag2.id).immutable is True

    def test_expired_tags_not_affected(self, initialized_db):
        """Dead tags excluded from retroactive enforcement."""
        org = create_org("retrouser9", "retro9@example.com", "retroorg9", "retroorg9@example.com")
        repo = create_repository(org.username, "retrorepo9", None)

        existing_repo = get_repository("devtable", "simple")
        manifest = _get_manifest_from_repo(existing_repo)

        # Create an expired tag
        tag_expired = _create_tag(repo, manifest, "v1.0.0", expired=True)
        tag_alive = _create_tag(repo, manifest, "v2.0.0", expired=False)

        create_namespace_immutability_policy(org.username, {"tag_pattern": "^v.*$"})

        # Expired tag should NOT be marked immutable
        assert Tag.get(Tag.id == tag_expired.id).immutable is False
        # Alive tag should be immutable
        assert Tag.get(Tag.id == tag_alive.id).immutable is True

    def test_hidden_tags_not_affected(self, initialized_db):
        """Temp tags excluded from retroactive enforcement."""
        org = create_org(
            "retrouser10", "retro10@example.com", "retroorg10", "retroorg10@example.com"
        )
        repo = create_repository(org.username, "retrorepo10", None)

        existing_repo = get_repository("devtable", "simple")
        manifest = _get_manifest_from_repo(existing_repo)

        # Create a hidden tag
        tag_hidden = _create_tag(repo, manifest, "v1.0.0", hidden=True)
        tag_visible = _create_tag(repo, manifest, "v2.0.0", hidden=False)

        create_namespace_immutability_policy(org.username, {"tag_pattern": "^v.*$"})

        # Hidden tag should NOT be marked immutable
        assert Tag.get(Tag.id == tag_hidden.id).immutable is False
        # Visible tag should be immutable
        assert Tag.get(Tag.id == tag_visible.id).immutable is True


class TestRetroactiveImmutabilityRollback:
    @patch(
        "data.model.immutability.apply_immutability_policy_to_existing_tags",
        side_effect=Exception("Simulated failure"),
    )
    def test_create_namespace_policy_rolls_back_on_failure(self, mock_apply, initialized_db):
        """Verify policy is deleted if retroactive enforcement fails on create."""
        org = create_org(
            "rollbackuser1",
            "rollback1@example.com",
            "rollbackorg1",
            "rollbackorg1@example.com",
        )

        # Attempt to create policy - should raise
        with pytest.raises(Exception, match="Simulated failure"):
            create_namespace_immutability_policy(org.username, {"tag_pattern": "^v.*$"})

        # Verify policy was rolled back (deleted)
        policies = get_namespace_immutability_policies(org.username)
        assert len(policies) == 0

    def test_update_namespace_policy_rolls_back_on_failure(self, initialized_db):
        """Verify policy is restored to old config if retroactive enforcement fails on update."""
        org = create_org(
            "rollbackuser2",
            "rollback2@example.com",
            "rollbackorg2",
            "rollbackorg2@example.com",
        )

        # Create policy successfully first (don't mock yet)
        policy = create_namespace_immutability_policy(
            org.username, {"tag_pattern": "^v.*$", "tag_pattern_matches": True}
        )

        # Now mock to fail on update
        with patch(
            "data.model.immutability.apply_immutability_policy_to_existing_tags",
            side_effect=Exception("Simulated failure"),
        ):
            # Attempt to update policy - should raise
            with pytest.raises(Exception, match="Simulated failure"):
                update_namespace_immutability_policy(
                    org.username, policy.uuid, {"tag_pattern": "^release-.*$"}
                )

        # Verify policy was rolled back to original config
        restored_policy = get_namespace_immutability_policy(org.username, policy.uuid)
        assert restored_policy is not None
        assert restored_policy.tag_pattern == "^v.*$"
        assert restored_policy.tag_pattern_matches is True

    @patch(
        "data.model.immutability.apply_immutability_policy_to_existing_tags",
        side_effect=Exception("Simulated failure"),
    )
    def test_create_repository_policy_rolls_back_on_failure(self, mock_apply, initialized_db):
        """Verify repository policy is deleted if retroactive enforcement fails on create."""
        org = create_org(
            "rollbackuser3",
            "rollback3@example.com",
            "rollbackorg3",
            "rollbackorg3@example.com",
        )
        repo = create_repository(org.username, "rollbackrepo3", None)

        # Attempt to create policy - should raise
        with pytest.raises(Exception, match="Simulated failure"):
            create_repository_immutability_policy(org.username, repo.name, {"tag_pattern": "^v.*$"})

        # Verify policy was rolled back (deleted)
        policies = get_repository_immutability_policies(org.username, repo.name)
        assert len(policies) == 0

    def test_update_repository_policy_rolls_back_on_failure(self, initialized_db):
        """Verify repository policy is restored to old config if retroactive fails on update."""
        org = create_org(
            "rollbackuser4",
            "rollback4@example.com",
            "rollbackorg4",
            "rollbackorg4@example.com",
        )
        repo = create_repository(org.username, "rollbackrepo4", None)

        # Create policy successfully first
        policy = create_repository_immutability_policy(
            org.username, repo.name, {"tag_pattern": "^v.*$", "tag_pattern_matches": True}
        )

        # Now mock to fail on update
        with patch(
            "data.model.immutability.apply_immutability_policy_to_existing_tags",
            side_effect=Exception("Simulated failure"),
        ):
            # Attempt to update policy - should raise
            with pytest.raises(Exception, match="Simulated failure"):
                update_repository_immutability_policy(
                    org.username, repo.name, policy.uuid, {"tag_pattern": "^release-.*$"}
                )

        # Verify policy was rolled back to original config
        restored_policy = get_repository_immutability_policy(org.username, repo.name, policy.uuid)
        assert restored_policy is not None
        assert restored_policy.tag_pattern == "^v.*$"
        assert restored_policy.tag_pattern_matches is True


@pytest.mark.usefixtures("initialized_db")
class TestNamespaceHasImmutableTags:
    def test_returns_false_when_no_immutable_tags(self):
        """Verify returns False when namespace has no immutable tags."""
        org = create_org(
            "hasimmuser1", "hasimm1@example.com", "hasimmorg1", "hasimmorg1@example.com"
        )
        repo = create_repository(org.username, "hasimmrepo1", None)

        existing_repo = get_repository("devtable", "simple")
        manifest = _get_manifest_from_repo(existing_repo)

        # Create some tags, none immutable
        _create_tag(repo, manifest, "v1.0.0", immutable=False)
        _create_tag(repo, manifest, "latest", immutable=False)

        assert namespace_has_immutable_tags(org.id) is False

    def test_returns_true_when_has_immutable_tags(self):
        """Verify returns True when namespace has immutable tags."""
        org = create_org(
            "hasimmuser2", "hasimm2@example.com", "hasimmorg2", "hasimmorg2@example.com"
        )
        repo = create_repository(org.username, "hasimmrepo2", None)

        existing_repo = get_repository("devtable", "simple")
        manifest = _get_manifest_from_repo(existing_repo)

        # Create an immutable tag
        _create_tag(repo, manifest, "v1.0.0", immutable=True)

        assert namespace_has_immutable_tags(org.id) is True

    def test_returns_true_with_multiple_repos_with_immutable_tags(self):
        """Verify returns True when multiple repos have immutable tags."""
        org = create_org(
            "hasimmuser3", "hasimm3@example.com", "hasimmorg3", "hasimmorg3@example.com"
        )
        repo1 = create_repository(org.username, "hasimmrepo3a", None)
        repo2 = create_repository(org.username, "hasimmrepo3b", None)
        repo3 = create_repository(org.username, "hasimmrepo3c", None)

        existing_repo = get_repository("devtable", "simple")
        manifest = _get_manifest_from_repo(existing_repo)

        # Create immutable tags in two repos
        _create_tag(repo1, manifest, "v1.0.0", immutable=True)
        _create_tag(repo2, manifest, "v1.0.0", immutable=True)
        _create_tag(repo3, manifest, "v1.0.0", immutable=False)

        assert namespace_has_immutable_tags(org.id) is True

    def test_ignores_expired_immutable_tags(self):
        """Verify expired immutable tags are not counted."""
        org = create_org(
            "hasimmuser4", "hasimm4@example.com", "hasimmorg4", "hasimmorg4@example.com"
        )
        repo = create_repository(org.username, "hasimmrepo4", None)

        existing_repo = get_repository("devtable", "simple")
        manifest = _get_manifest_from_repo(existing_repo)

        # Create an expired immutable tag
        _create_tag(repo, manifest, "v1.0.0", immutable=True, expired=True)

        assert namespace_has_immutable_tags(org.id) is False

    def test_ignores_hidden_immutable_tags(self):
        """Verify hidden immutable tags are not counted."""
        org = create_org(
            "hasimmuser5", "hasimm5@example.com", "hasimmorg5", "hasimmorg5@example.com"
        )
        repo = create_repository(org.username, "hasimmrepo5", None)

        existing_repo = get_repository("devtable", "simple")
        manifest = _get_manifest_from_repo(existing_repo)

        # Create a hidden immutable tag
        _create_tag(repo, manifest, "v1.0.0", immutable=True, hidden=True)

        assert namespace_has_immutable_tags(org.id) is False
