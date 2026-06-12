import json
import uuid

import pytest

from data.database import (
    LogEntry3,
    LogEntryKind,
    QuarantinedRepository,
    Repository,
    SpamDetectionRule,
)
from data.model.repository import get_repository
from data.model.spam import (
    VALID_RULE_TYPES,
    VALID_STATUSES,
    InvalidSpamDetectionRule,
    InvalidStatusTransition,
    QuarantinedRepoNotFound,
    QuarantinedRepoView,
    SpamDetectionRuleNotFound,
    SpamDetectionRuleView,
    create_quarantined_repo,
    create_spam_detection_rule,
    delete_spam_detection_rule,
    dismiss_quarantined_repo,
    get_quarantined_repo_by_uuid,
    get_quarantined_repos,
    get_spam_detection_rule_by_uuid,
    get_spam_detection_rules,
    quarantine_repository,
    repo_already_flagged,
    restore_repository,
    update_spam_detection_rule,
    validate_spam_rule,
)
from test.fixtures import *


@pytest.fixture()
def cleanup_spam_tables(initialized_db):
    QuarantinedRepository.delete().execute()
    SpamDetectionRule.delete().execute()


@pytest.fixture()
def sample_rule(cleanup_spam_tables):
    return create_spam_detection_rule(
        name="test keyword rule",
        rule_type="keyword",
        pattern="spam.*test",
        confidence_score=75,
    )


@pytest.fixture()
def sample_repo(cleanup_spam_tables):
    repo = get_repository("devtable", "simple")
    return repo


@pytest.fixture()
def sample_quarantined_repo(sample_repo):
    return create_quarantined_repo(
        repository=sample_repo.id,
        namespace_name="devtable",
        repo_name="simple",
        original_description="A simple repository",
        matched_rules=[{"rule": "keyword", "pattern": "spam"}],
        total_confidence=80,
        is_empty=False,
        scan_id="scan-001",
    )


def _get_repo_spam_logs(kind_name, repository_id):
    kind = LogEntryKind.get(LogEntryKind.name == kind_name)
    return list(
        LogEntry3.select()
        .where(
            LogEntry3.kind == kind.id,
            LogEntry3.repository == repository_id,
        )
        .order_by(LogEntry3.id)
    )


class TestConstants:
    def test_valid_rule_types(self):
        assert VALID_RULE_TYPES == {
            "keyword",
            "url_pattern",
            "repo_name_pattern",
            "empty_repo",
            "account_age",
        }

    def test_valid_statuses(self):
        assert "flagged" in VALID_STATUSES
        assert "quarantined" in VALID_STATUSES
        assert "restored" in VALID_STATUSES
        assert "dismissed" in VALID_STATUSES


class TestValidateSpamRule:
    @pytest.mark.parametrize("rule_type", sorted(VALID_RULE_TYPES))
    def test_valid_rule_types(self, rule_type):
        pattern = "test" if rule_type in ("url_pattern", "repo_name_pattern") else None
        validate_spam_rule(rule_type, pattern=pattern, confidence_score=50)

    def test_invalid_rule_type(self):
        with pytest.raises(InvalidSpamDetectionRule, match="Invalid rule_type"):
            validate_spam_rule("nonexistent_type")

    def test_confidence_score_zero(self):
        validate_spam_rule("keyword", confidence_score=0)

    def test_confidence_score_hundred(self):
        validate_spam_rule("keyword", confidence_score=100)

    def test_confidence_score_negative(self):
        with pytest.raises(InvalidSpamDetectionRule, match="confidence_score must be an integer"):
            validate_spam_rule("keyword", confidence_score=-1)

    def test_confidence_score_over_hundred(self):
        with pytest.raises(InvalidSpamDetectionRule, match="confidence_score must be an integer"):
            validate_spam_rule("keyword", confidence_score=101)

    def test_confidence_score_float(self):
        with pytest.raises(InvalidSpamDetectionRule, match="confidence_score must be an integer"):
            validate_spam_rule("keyword", confidence_score=50.5)

    def test_confidence_score_string(self):
        with pytest.raises(InvalidSpamDetectionRule, match="confidence_score must be an integer"):
            validate_spam_rule("keyword", confidence_score="50")

    def test_valid_url_pattern_regex(self):
        validate_spam_rule("url_pattern", pattern=r"https?://example\.com/.*")

    def test_valid_repo_name_pattern_regex(self):
        validate_spam_rule("repo_name_pattern", pattern=r"^spam-\d+$")

    def test_invalid_url_pattern_regex(self):
        with pytest.raises(InvalidSpamDetectionRule, match="Invalid regex pattern"):
            validate_spam_rule("url_pattern", pattern="[invalid(regex")

    def test_invalid_repo_name_pattern_regex(self):
        with pytest.raises(InvalidSpamDetectionRule, match="Invalid regex pattern"):
            validate_spam_rule("repo_name_pattern", pattern="(unclosed")

    def test_keyword_with_pattern_no_regex_validation(self):
        validate_spam_rule("keyword", pattern="[not-a-valid-regex(")

    def test_empty_repo_with_pattern_no_regex_validation(self):
        validate_spam_rule("empty_repo", pattern="[invalid(")

    def test_account_age_with_pattern_no_regex_validation(self):
        validate_spam_rule("account_age", pattern="[invalid(")

    def test_url_pattern_none_pattern_raises(self):
        with pytest.raises(InvalidSpamDetectionRule, match="pattern is required"):
            validate_spam_rule("url_pattern", pattern=None)

    def test_repo_name_pattern_none_pattern_raises(self):
        with pytest.raises(InvalidSpamDetectionRule, match="pattern is required"):
            validate_spam_rule("repo_name_pattern", pattern=None)

    def test_url_pattern_empty_string_raises(self):
        with pytest.raises(InvalidSpamDetectionRule, match="pattern is required"):
            validate_spam_rule("url_pattern", pattern="")


class TestSpamDetectionRuleView:
    def test_get_view(self, sample_rule):
        view = sample_rule.get_view()
        assert view["name"] == "test keyword rule"
        assert view["rule_type"] == "keyword"
        assert view["pattern"] == "spam.*test"
        assert view["confidence_score"] == 75
        assert view["enabled"] is True
        assert view["config"] == {}
        assert view["uuid"] is not None
        assert view["created_at"] is not None
        assert view["updated_at"] is not None

    def test_view_attributes(self, sample_rule):
        assert isinstance(sample_rule, SpamDetectionRuleView)
        assert sample_rule.name == "test keyword rule"
        assert sample_rule.rule_type == "keyword"
        assert sample_rule.pattern == "spam.*test"
        assert sample_rule.confidence_score == 75
        assert sample_rule.enabled is True

    def test_view_config_defaults_to_empty_dict(self, cleanup_spam_tables):
        rule = create_spam_detection_rule(
            name="no config rule",
            rule_type="keyword",
            config=None,
        )
        assert rule.config == {}


class TestCreateSpamDetectionRule:
    def test_create_with_defaults(self, cleanup_spam_tables):
        rule = create_spam_detection_rule(name="basic rule", rule_type="keyword")
        assert rule.name == "basic rule"
        assert rule.rule_type == "keyword"
        assert rule.pattern is None
        assert rule.confidence_score == 50
        assert rule.enabled is True
        assert rule.config == {}

    def test_create_with_all_fields(self, cleanup_spam_tables):
        rule = create_spam_detection_rule(
            name="full rule",
            rule_type="url_pattern",
            pattern=r"https?://spam\.com",
            config={"threshold": 10},
            confidence_score=90,
        )
        assert rule.name == "full rule"
        assert rule.rule_type == "url_pattern"
        assert rule.pattern == r"https?://spam\.com"
        assert rule.config == {"threshold": 10}
        assert rule.confidence_score == 90

    @pytest.mark.parametrize("rule_type", sorted(VALID_RULE_TYPES))
    def test_create_each_rule_type(self, cleanup_spam_tables, rule_type):
        pattern = "test" if rule_type in ("url_pattern", "repo_name_pattern") else None
        rule = create_spam_detection_rule(
            name=f"rule-{rule_type}", rule_type=rule_type, pattern=pattern
        )
        assert rule.rule_type == rule_type

    def test_create_with_invalid_type_raises(self, cleanup_spam_tables):
        with pytest.raises(InvalidSpamDetectionRule):
            create_spam_detection_rule(name="bad", rule_type="invalid_type")

    def test_create_with_invalid_confidence_raises(self, cleanup_spam_tables):
        with pytest.raises(InvalidSpamDetectionRule):
            create_spam_detection_rule(name="bad", rule_type="keyword", confidence_score=150)

    def test_create_with_invalid_regex_raises(self, cleanup_spam_tables):
        with pytest.raises(InvalidSpamDetectionRule):
            create_spam_detection_rule(
                name="bad regex",
                rule_type="url_pattern",
                pattern="[invalid(",
            )


class TestGetSpamDetectionRules:
    def test_get_all_rules(self, cleanup_spam_tables):
        create_spam_detection_rule(name="rule1", rule_type="keyword")
        create_spam_detection_rule(name="rule2", rule_type="empty_repo")
        rules = get_spam_detection_rules()
        assert len(rules) >= 2
        names = {r.name for r in rules}
        assert "rule1" in names
        assert "rule2" in names

    def test_get_enabled_only(self, cleanup_spam_tables):
        r1 = create_spam_detection_rule(name="enabled", rule_type="keyword")
        r2 = create_spam_detection_rule(name="to_disable", rule_type="keyword")
        update_spam_detection_rule(r2.uuid, enabled=False)

        enabled_rules = get_spam_detection_rules(enabled_only=True)
        enabled_names = {r.name for r in enabled_rules}
        assert "enabled" in enabled_names
        assert "to_disable" not in enabled_names

    def test_get_all_includes_disabled(self, cleanup_spam_tables):
        r1 = create_spam_detection_rule(name="enabled", rule_type="keyword")
        r2 = create_spam_detection_rule(name="disabled", rule_type="keyword")
        update_spam_detection_rule(r2.uuid, enabled=False)

        all_rules = get_spam_detection_rules(enabled_only=False)
        names = {r.name for r in all_rules}
        assert "enabled" in names
        assert "disabled" in names

    def test_get_rules_empty_table(self, cleanup_spam_tables):
        rules = get_spam_detection_rules()
        assert rules == []


class TestGetSpamDetectionRuleByUuid:
    def test_found(self, sample_rule):
        result = get_spam_detection_rule_by_uuid(sample_rule.uuid)
        assert result is not None
        assert result.uuid == sample_rule.uuid
        assert result.name == sample_rule.name
        assert isinstance(result, SpamDetectionRuleView)

    def test_not_found(self, cleanup_spam_tables):
        result = get_spam_detection_rule_by_uuid("nonexistent-uuid")
        assert result is None


class TestUpdateSpamDetectionRule:
    def test_update_name(self, sample_rule):
        result = update_spam_detection_rule(sample_rule.uuid, name="updated name")
        assert result is True
        updated = get_spam_detection_rule_by_uuid(sample_rule.uuid)
        assert updated.name == "updated name"

    def test_update_rule_type(self, sample_rule):
        update_spam_detection_rule(sample_rule.uuid, rule_type="empty_repo")
        updated = get_spam_detection_rule_by_uuid(sample_rule.uuid)
        assert updated.rule_type == "empty_repo"

    def test_update_pattern(self, sample_rule):
        update_spam_detection_rule(sample_rule.uuid, pattern="new_pattern")
        updated = get_spam_detection_rule_by_uuid(sample_rule.uuid)
        assert updated.pattern == "new_pattern"

    def test_update_config(self, sample_rule):
        update_spam_detection_rule(sample_rule.uuid, config={"key": "value"})
        updated = get_spam_detection_rule_by_uuid(sample_rule.uuid)
        assert updated.config == {"key": "value"}

    def test_update_confidence_score(self, sample_rule):
        update_spam_detection_rule(sample_rule.uuid, confidence_score=100)
        updated = get_spam_detection_rule_by_uuid(sample_rule.uuid)
        assert updated.confidence_score == 100

    def test_update_enabled(self, sample_rule):
        update_spam_detection_rule(sample_rule.uuid, enabled=False)
        updated = get_spam_detection_rule_by_uuid(sample_rule.uuid)
        assert updated.enabled is False

    def test_update_multiple_fields(self, sample_rule):
        update_spam_detection_rule(
            sample_rule.uuid,
            name="multi update",
            confidence_score=99,
            enabled=False,
        )
        updated = get_spam_detection_rule_by_uuid(sample_rule.uuid)
        assert updated.name == "multi update"
        assert updated.confidence_score == 99
        assert updated.enabled is False

    def test_update_sets_updated_at(self, sample_rule):
        original_updated = sample_rule.updated_at
        update_spam_detection_rule(sample_rule.uuid, name="timestamp check")
        updated = get_spam_detection_rule_by_uuid(sample_rule.uuid)
        assert updated.updated_at >= original_updated

    def test_update_nonexistent_raises(self, cleanup_spam_tables):
        with pytest.raises(SpamDetectionRuleNotFound, match="not found"):
            update_spam_detection_rule("nonexistent-uuid", name="nope")

    def test_update_with_invalid_rule_type_raises(self, sample_rule):
        with pytest.raises(InvalidSpamDetectionRule):
            update_spam_detection_rule(sample_rule.uuid, rule_type="bad_type")

    def test_update_with_invalid_confidence_raises(self, sample_rule):
        with pytest.raises(InvalidSpamDetectionRule):
            update_spam_detection_rule(sample_rule.uuid, confidence_score=-5)

    def test_update_with_invalid_regex_raises(self, sample_rule):
        with pytest.raises(InvalidSpamDetectionRule):
            update_spam_detection_rule(sample_rule.uuid, rule_type="url_pattern", pattern="[bad(")

    def test_update_no_allowed_fields_returns_true(self, sample_rule):
        result = update_spam_detection_rule(sample_rule.uuid, not_a_real_field="value")
        assert result is True

    def test_update_empty_fields_returns_true(self, sample_rule):
        result = update_spam_detection_rule(sample_rule.uuid)
        assert result is True


class TestDeleteSpamDetectionRule:
    def test_delete_existing(self, sample_rule):
        result = delete_spam_detection_rule(sample_rule.uuid)
        assert result is True
        assert get_spam_detection_rule_by_uuid(sample_rule.uuid) is None

    def test_delete_nonexistent_raises(self, cleanup_spam_tables):
        with pytest.raises(SpamDetectionRuleNotFound, match="not found"):
            delete_spam_detection_rule("nonexistent-uuid")


class TestQuarantinedRepoView:
    def test_get_view(self, sample_quarantined_repo):
        view = sample_quarantined_repo.get_view()
        assert view["namespace_name"] == "devtable"
        assert view["repository_name"] == "simple"
        assert view["status"] == "flagged"
        assert view["original_description"] == "A simple repository"
        assert view["matched_rules"] == [{"rule": "keyword", "pattern": "spam"}]
        assert view["total_confidence_score"] == 80
        assert view["is_empty"] is False
        assert view["scan_id"] == "scan-001"
        assert view["actioned_by"] is None
        assert view["actioned_at"] is None
        assert view["created_at"] is not None
        assert view["updated_at"] is not None
        assert view["uuid"] is not None

    def test_view_attributes(self, sample_quarantined_repo):
        assert isinstance(sample_quarantined_repo, QuarantinedRepoView)
        assert sample_quarantined_repo.namespace_name == "devtable"
        assert sample_quarantined_repo.repository_name == "simple"
        assert sample_quarantined_repo.status == "flagged"

    def test_matched_rules_defaults_to_list(self, sample_repo):
        qr = create_quarantined_repo(
            repository=sample_repo.id,
            namespace_name="devtable",
            repo_name="simple",
            original_description=None,
            matched_rules=None,
            total_confidence=50,
            is_empty=True,
            scan_id="scan-x",
        )
        assert qr.matched_rules == []


class TestCreateQuarantinedRepo:
    def test_create_basic(self, sample_repo, cleanup_spam_tables):
        qr = create_quarantined_repo(
            repository=sample_repo.id,
            namespace_name="devtable",
            repo_name="simple",
            original_description="desc",
            matched_rules=[{"rule": "test"}],
            total_confidence=60,
            is_empty=False,
            scan_id="scan-100",
        )
        assert isinstance(qr, QuarantinedRepoView)
        assert qr.namespace_name == "devtable"
        assert qr.repository_name == "simple"
        assert qr.original_description == "desc"
        assert qr.total_confidence_score == 60
        assert qr.is_empty is False
        assert qr.scan_id == "scan-100"
        assert qr.status == "flagged"
        assert qr.uuid is not None

    def test_create_empty_repo(self, sample_repo, cleanup_spam_tables):
        qr = create_quarantined_repo(
            repository=sample_repo.id,
            namespace_name="devtable",
            repo_name="simple",
            original_description=None,
            matched_rules=[],
            total_confidence=30,
            is_empty=True,
            scan_id="scan-empty",
        )
        assert qr.is_empty is True
        assert qr.original_description is None


class TestGetQuarantinedRepos:
    def test_get_all(self, sample_quarantined_repo):
        repos, next_token = get_quarantined_repos()
        assert len(repos) >= 1
        uuids = {r.uuid for r in repos}
        assert sample_quarantined_repo.uuid in uuids

    def test_filter_by_status(self, sample_quarantined_repo):
        repos, _ = get_quarantined_repos(status="flagged")
        assert len(repos) >= 1
        assert all(r.status == "flagged" for r in repos)

    def test_filter_by_status_no_results(self, sample_quarantined_repo):
        repos, _ = get_quarantined_repos(status="dismissed")
        assert len(repos) == 0

    def test_filter_by_min_confidence(self, sample_quarantined_repo):
        repos, _ = get_quarantined_repos(min_confidence=80)
        assert len(repos) >= 1
        assert all(r.total_confidence_score >= 80 for r in repos)

    def test_filter_by_min_confidence_excludes_lower(self, sample_quarantined_repo):
        repos, _ = get_quarantined_repos(min_confidence=81)
        assert len(repos) == 0

    def test_filter_by_namespace(self, sample_quarantined_repo):
        repos, _ = get_quarantined_repos(namespace="devtable")
        assert len(repos) >= 1
        assert all(r.namespace_name == "devtable" for r in repos)

    def test_filter_by_namespace_no_results(self, sample_quarantined_repo):
        repos, _ = get_quarantined_repos(namespace="nonexistent_namespace")
        assert len(repos) == 0

    def test_filter_by_scan_id(self, sample_quarantined_repo):
        repos, _ = get_quarantined_repos(scan_id="scan-001")
        assert len(repos) >= 1
        assert all(r.scan_id == "scan-001" for r in repos)

    def test_filter_by_scan_id_no_results(self, sample_quarantined_repo):
        repos, _ = get_quarantined_repos(scan_id="nonexistent-scan")
        assert len(repos) == 0

    def test_combined_filters(self, sample_quarantined_repo):
        repos, _ = get_quarantined_repos(
            status="flagged",
            namespace="devtable",
            scan_id="scan-001",
            min_confidence=50,
        )
        assert len(repos) >= 1

    def test_orders_by_confidence_desc_then_id_desc(self, cleanup_spam_tables):
        test_repos = [
            get_repository("devtable", "simple"),
            get_repository("devtable", "complex"),
            get_repository("devtable", "history"),
        ]
        scores = [75, 90, 90]
        for repo, score in zip(test_repos, scores):
            create_quarantined_repo(
                repository=repo.id,
                namespace_name="devtable",
                repo_name=repo.name,
                original_description=f"desc-{repo.name}",
                matched_rules=[],
                total_confidence=score,
                is_empty=False,
                scan_id=f"scan-page-{repo.name}",
            )

        repos, _ = get_quarantined_repos()
        returned = [(repo.total_confidence_score, repo.repository_name) for repo in repos]
        assert returned[:3] == [(90, "history"), (90, "complex"), (75, "simple")]

    def test_pagination_limit_uses_confidence_order(self, cleanup_spam_tables):
        test_repos = [
            get_repository("devtable", "simple"),
            get_repository("devtable", "complex"),
            get_repository("devtable", "history"),
        ]
        for repo, score in zip(test_repos, [75, 90, 90]):
            create_quarantined_repo(
                repository=repo.id,
                namespace_name="devtable",
                repo_name=repo.name,
                original_description=f"desc-{repo.name}",
                matched_rules=[],
                total_confidence=score,
                is_empty=False,
                scan_id=f"scan-page-{repo.name}",
            )

        repos, next_token = get_quarantined_repos(limit=2)
        assert len(repos) == 2
        assert [repo.total_confidence_score for repo in repos] == [90, 90]
        assert next_token is not None

        next_page, final_token = get_quarantined_repos(limit=2, page_token=next_token)
        assert [repo.total_confidence_score for repo in next_page] == [75]
        assert {repo.uuid for repo in repos}.isdisjoint({repo.uuid for repo in next_page})
        assert final_token is None

    def test_empty_results(self, cleanup_spam_tables):
        repos, next_token = get_quarantined_repos()
        assert repos == []


class TestGetQuarantinedRepoByUuid:
    def test_found(self, sample_quarantined_repo):
        result = get_quarantined_repo_by_uuid(sample_quarantined_repo.uuid)
        assert result is not None
        assert result.uuid == sample_quarantined_repo.uuid
        assert isinstance(result, QuarantinedRepoView)

    def test_not_found(self, cleanup_spam_tables):
        result = get_quarantined_repo_by_uuid("nonexistent-uuid")
        assert result is None


class TestRepoAlreadyFlagged:
    def test_flagged_repo_returns_true(self, sample_quarantined_repo):
        assert repo_already_flagged(sample_quarantined_repo.repository_id) is True

    def test_unflagged_repo_returns_false(self, cleanup_spam_tables):
        repo = get_repository("devtable", "simple")
        assert repo_already_flagged(repo.id) is False

    def test_dismissed_repo_returns_false(self, sample_quarantined_repo):
        dismiss_quarantined_repo(sample_quarantined_repo.uuid, actioned_by="admin")
        assert repo_already_flagged(sample_quarantined_repo.repository_id) is False

    def test_quarantined_repo_returns_true(self, sample_quarantined_repo):
        quarantine_repository(sample_quarantined_repo.uuid, actioned_by="admin")
        assert repo_already_flagged(sample_quarantined_repo.repository_id) is True

    def test_restored_repo_returns_false(self, sample_quarantined_repo):
        quarantine_repository(sample_quarantined_repo.uuid, actioned_by="admin")
        restore_repository(sample_quarantined_repo.uuid, actioned_by="admin")
        assert repo_already_flagged(sample_quarantined_repo.repository_id) is False


class TestQuarantineRepository:
    def test_quarantine_sets_status(self, sample_quarantined_repo):
        result = quarantine_repository(sample_quarantined_repo.uuid, actioned_by="admin_user")
        assert result is True
        updated = get_quarantined_repo_by_uuid(sample_quarantined_repo.uuid)
        assert updated.status == "quarantined"
        assert updated.actioned_by == "admin_user"
        assert updated.actioned_at is not None

    def test_quarantine_clears_repo_description(self, sample_quarantined_repo):
        quarantine_repository(sample_quarantined_repo.uuid, actioned_by="admin")
        repo = (
            Repository.select().where(Repository.id == sample_quarantined_repo.repository_id).get()
        )
        assert repo.description is None

    def test_quarantine_nonexistent_raises(self, cleanup_spam_tables):
        with pytest.raises(QuarantinedRepoNotFound, match="not found"):
            quarantine_repository("nonexistent-uuid", actioned_by="admin")

    def test_quarantine_already_quarantined_raises(self, sample_quarantined_repo):
        quarantine_repository(sample_quarantined_repo.uuid, actioned_by="admin")
        with pytest.raises(InvalidStatusTransition, match="must be 'flagged'"):
            quarantine_repository(sample_quarantined_repo.uuid, actioned_by="admin")

    def test_quarantine_restored_raises(self, sample_quarantined_repo):
        quarantine_repository(sample_quarantined_repo.uuid, actioned_by="admin")
        restore_repository(sample_quarantined_repo.uuid, actioned_by="admin")
        with pytest.raises(InvalidStatusTransition, match="must be 'flagged'"):
            quarantine_repository(sample_quarantined_repo.uuid, actioned_by="admin")

    def test_quarantine_dismissed_raises(self, sample_quarantined_repo):
        dismiss_quarantined_repo(sample_quarantined_repo.uuid, actioned_by="admin")
        with pytest.raises(InvalidStatusTransition, match="must be 'flagged'"):
            quarantine_repository(sample_quarantined_repo.uuid, actioned_by="admin")

    def test_quarantine_writes_audit_log(self, sample_quarantined_repo):
        quarantine_repository(sample_quarantined_repo.uuid, actioned_by="admin")

        logs = _get_repo_spam_logs("spam_repo_quarantined", sample_quarantined_repo.repository_id)
        assert len(logs) == 1

        metadata = json.loads(logs[0].metadata_json)
        assert metadata["repo"] == "simple"
        assert metadata["namespace"] == "devtable"
        assert metadata["quarantined_repo_uuid"] == sample_quarantined_repo.uuid
        assert metadata["status"] == "quarantined"


class TestRestoreRepository:
    def test_restore_sets_status(self, sample_quarantined_repo):
        quarantine_repository(sample_quarantined_repo.uuid, actioned_by="admin")
        result = restore_repository(sample_quarantined_repo.uuid, actioned_by="admin_user")
        assert result is True
        updated = get_quarantined_repo_by_uuid(sample_quarantined_repo.uuid)
        assert updated.status == "restored"
        assert updated.actioned_by == "admin_user"
        assert updated.actioned_at is not None

    def test_restore_reinstates_description(self, sample_quarantined_repo):
        quarantine_repository(sample_quarantined_repo.uuid, actioned_by="admin")
        repo = (
            Repository.select().where(Repository.id == sample_quarantined_repo.repository_id).get()
        )
        assert repo.description is None

        restore_repository(sample_quarantined_repo.uuid, actioned_by="admin")
        repo = (
            Repository.select().where(Repository.id == sample_quarantined_repo.repository_id).get()
        )
        assert repo.description == "A simple repository"

    def test_restore_nonexistent_raises(self, cleanup_spam_tables):
        with pytest.raises(QuarantinedRepoNotFound, match="not found"):
            restore_repository("nonexistent-uuid", actioned_by="admin")

    def test_restore_flagged_raises(self, sample_quarantined_repo):
        with pytest.raises(InvalidStatusTransition, match="must be 'quarantined'"):
            restore_repository(sample_quarantined_repo.uuid, actioned_by="admin")

    def test_restore_dismissed_raises(self, sample_quarantined_repo):
        dismiss_quarantined_repo(sample_quarantined_repo.uuid, actioned_by="admin")
        with pytest.raises(InvalidStatusTransition, match="must be 'quarantined'"):
            restore_repository(sample_quarantined_repo.uuid, actioned_by="admin")

    def test_restore_writes_audit_log(self, sample_quarantined_repo):
        quarantine_repository(sample_quarantined_repo.uuid, actioned_by="admin")
        restore_repository(sample_quarantined_repo.uuid, actioned_by="admin")

        logs = _get_repo_spam_logs("spam_repo_restored", sample_quarantined_repo.repository_id)
        assert len(logs) == 1

        metadata = json.loads(logs[0].metadata_json)
        assert metadata["repo"] == "simple"
        assert metadata["namespace"] == "devtable"
        assert metadata["quarantined_repo_uuid"] == sample_quarantined_repo.uuid
        assert metadata["status"] == "restored"


class TestDismissQuarantinedRepo:
    def test_dismiss_sets_status(self, sample_quarantined_repo):
        result = dismiss_quarantined_repo(sample_quarantined_repo.uuid, actioned_by="mod_user")
        assert result is True
        updated = get_quarantined_repo_by_uuid(sample_quarantined_repo.uuid)
        assert updated.status == "dismissed"
        assert updated.actioned_by == "mod_user"
        assert updated.actioned_at is not None

    def test_dismiss_nonexistent_raises(self, cleanup_spam_tables):
        with pytest.raises(QuarantinedRepoNotFound, match="not found"):
            dismiss_quarantined_repo("nonexistent-uuid", actioned_by="admin")

    def test_dismiss_restored_raises(self, sample_quarantined_repo):
        quarantine_repository(sample_quarantined_repo.uuid, actioned_by="admin")
        restore_repository(sample_quarantined_repo.uuid, actioned_by="admin")
        with pytest.raises(InvalidStatusTransition, match="must be 'flagged' or 'quarantined'"):
            dismiss_quarantined_repo(sample_quarantined_repo.uuid, actioned_by="admin")

    def test_dismiss_already_dismissed_raises(self, sample_quarantined_repo):
        dismiss_quarantined_repo(sample_quarantined_repo.uuid, actioned_by="admin")
        with pytest.raises(InvalidStatusTransition, match="must be 'flagged' or 'quarantined'"):
            dismiss_quarantined_repo(sample_quarantined_repo.uuid, actioned_by="admin")

    def test_dismiss_writes_audit_log(self, sample_quarantined_repo):
        dismiss_quarantined_repo(sample_quarantined_repo.uuid, actioned_by="admin")

        logs = _get_repo_spam_logs("spam_repo_dismissed", sample_quarantined_repo.repository_id)
        assert len(logs) == 1

        metadata = json.loads(logs[0].metadata_json)
        assert metadata["repo"] == "simple"
        assert metadata["namespace"] == "devtable"
        assert metadata["quarantined_repo_uuid"] == sample_quarantined_repo.uuid
        assert metadata["status"] == "dismissed"


class TestSpamSeedData:
    def test_log_entry_kinds_exist(self, initialized_db):
        from data.database import LogEntryKind

        for kind_name in ("spam_repo_quarantined", "spam_repo_restored", "spam_repo_dismissed"):
            assert LogEntryKind.get_or_none(LogEntryKind.name == kind_name) is not None

    def test_notification_kind_exists(self, initialized_db):
        from data.database import NotificationKind

        assert (
            NotificationKind.get_or_none(NotificationKind.name == "repo_spam_quarantined")
            is not None
        )

    def test_quarantine_creates_notification(self, sample_quarantined_repo):
        from data.database import Notification, NotificationKind

        quarantine_repository(sample_quarantined_repo.uuid, actioned_by="admin")
        kind = NotificationKind.get(NotificationKind.name == "repo_spam_quarantined")
        repo = (
            Repository.select().where(Repository.id == sample_quarantined_repo.repository_id).get()
        )
        notifications = list(
            Notification.select().where(
                Notification.kind == kind,
                Notification.target == repo.namespace_user_id,
            )
        )
        assert len(notifications) >= 1


class TestExceptionClasses:
    def test_invalid_spam_detection_rule_is_data_model_exception(self):
        from data.model import DataModelException

        assert issubclass(InvalidSpamDetectionRule, DataModelException)

    def test_spam_detection_rule_not_found_is_data_model_exception(self):
        from data.model import DataModelException

        assert issubclass(SpamDetectionRuleNotFound, DataModelException)

    def test_quarantined_repo_not_found_is_data_model_exception(self):
        from data.model import DataModelException

        assert issubclass(QuarantinedRepoNotFound, DataModelException)
