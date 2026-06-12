import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from data.database import QuarantinedRepository, Repository, SpamDetectionRule
from data.model.repository import get_repository
from data.model.spam import create_quarantined_repo, create_spam_detection_rule
from data.model.spam_detection_engine import (
    REGEX_EVAL_TIMEOUT_SECS,
    RuleEvaluator,
    RuleMatch,
    ScanConfig,
    ScanReport,
    SpamScanner,
    _regex_search_with_timeout,
)
from test.fixtures import *


def make_rule_view(
    rule_type,
    pattern=None,
    config=None,
    uuid_val="test-uuid",
    confidence_score=50,
    name="test-rule",
):
    rv = MagicMock()
    rv.rule_type = rule_type
    rv.pattern = pattern
    rv.config = config or {}
    rv.uuid = uuid_val
    rv.confidence_score = confidence_score
    rv.name = name
    rv.enabled = True
    return rv


def make_repo(name="test-repo", description="some description", repo_id=1):
    repo = MagicMock(spec=["name", "description", "id", "namespace_user"])
    repo.name = name
    repo.description = description
    repo.id = repo_id
    return repo


class TestScanConfig:
    def test_scan_config_defaults(self):
        config = ScanConfig()
        assert config.batch_size == 200
        assert config.sleep_between_batches == 0.5
        assert config.min_confidence_threshold == 50
        assert config.dry_run is True
        assert config.scan_id is not None
        uuid.UUID(config.scan_id)

    def test_scan_config_custom_values(self):
        config = ScanConfig(
            batch_size=500,
            sleep_between_batches=1.0,
            min_confidence_threshold=75,
            dry_run=False,
            scan_id="custom-scan-id",
        )
        assert config.batch_size == 500
        assert config.sleep_between_batches == 1.0
        assert config.min_confidence_threshold == 75
        assert config.dry_run is False
        assert config.scan_id == "custom-scan-id"


class TestRuleMatch:
    def test_rule_match_creation(self):
        match = RuleMatch(
            rule_uuid="abc-123",
            rule_name="keyword check",
            rule_type="keyword",
            confidence=80,
        )
        assert match.rule_uuid == "abc-123"
        assert match.rule_name == "keyword check"
        assert match.rule_type == "keyword"
        assert match.confidence == 80


class TestScanReport:
    def test_scan_report_to_dict(self):
        report = ScanReport(
            scan_id="scan-1",
            total_scanned=10,
            flagged=2,
            skipped=1,
            clean=5,
            below_threshold=1,
            errors=1,
        )
        d = report.to_dict()
        assert d["scan_id"] == "scan-1"
        assert d["total_scanned"] == 10
        assert d["flagged"] == 2
        assert d["skipped"] == 1
        assert d["clean"] == 5
        assert d["below_threshold"] == 1
        assert d["errors"] == 1
        assert d["started_at"] is None
        assert d["finished_at"] is None

    def test_scan_report_to_dict_with_datetimes(self):
        started = datetime(2026, 1, 15, 10, 30, 0)
        finished = datetime(2026, 1, 15, 10, 35, 0)
        report = ScanReport(
            scan_id="scan-2",
            started_at=started,
            finished_at=finished,
        )
        d = report.to_dict()
        assert d["started_at"] == str(started)
        assert d["finished_at"] == str(finished)


class TestRuleEvaluatorKeyword:
    def test_eval_keyword_match(self):
        rule_view = make_rule_view("keyword", pattern="free,bitcoin")
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo(description="Get free stuff here")
        assert evaluator.evaluate(repo) is True

    def test_eval_keyword_no_match(self):
        rule_view = make_rule_view("keyword", pattern="free,bitcoin")
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo(description="A normal container image")
        assert evaluator.evaluate(repo) is False

    def test_eval_keyword_no_description(self):
        rule_view = make_rule_view("keyword", pattern="free")
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo(description=None)
        assert evaluator.evaluate(repo) is False

    def test_eval_keyword_no_pattern(self):
        rule_view = make_rule_view("keyword", pattern=None)
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo(description="some description")
        assert evaluator.evaluate(repo) is False

    def test_eval_keyword_case_insensitive(self):
        rule_view = make_rule_view("keyword", pattern="Bitcoin")
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo(description="BITCOIN mining tools")
        assert evaluator.evaluate(repo) is True

    def test_eval_keyword_multiple_keywords(self):
        rule_view = make_rule_view("keyword", pattern="spam,phishing,malware")
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo(description="This repo has phishing tools")
        assert evaluator.evaluate(repo) is True


class TestRuleEvaluatorUrlPattern:
    def test_eval_url_pattern_match(self):
        rule_view = make_rule_view("url_pattern", pattern=r"https?://evil\.com")
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo(description="Visit http://evil.com for details")
        assert evaluator.evaluate(repo) is True

    def test_eval_url_pattern_no_match(self):
        rule_view = make_rule_view("url_pattern", pattern=r"https?://evil\.com")
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo(description="A perfectly safe repo")
        assert evaluator.evaluate(repo) is False

    def test_eval_url_pattern_no_description(self):
        rule_view = make_rule_view("url_pattern", pattern=r"https?://evil\.com")
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo(description=None)
        assert evaluator.evaluate(repo) is False


class TestRuleEvaluatorRepoNamePattern:
    def test_eval_repo_name_pattern_match(self):
        rule_view = make_rule_view("repo_name_pattern", pattern=r"^spam-.*")
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo(name="spam-repo-123")
        assert evaluator.evaluate(repo) is True

    def test_eval_repo_name_pattern_no_match(self):
        rule_view = make_rule_view("repo_name_pattern", pattern=r"^spam-.*")
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo(name="legitimate-repo")
        assert evaluator.evaluate(repo) is False


class TestRuleEvaluatorEmptyRepo:
    @patch("data.model.spam_detection_engine.Tag")
    def test_eval_empty_repo_true(self, mock_tag):
        mock_tag.select.return_value.where.return_value.limit.return_value.exists.return_value = (
            False
        )
        rule_view = make_rule_view("empty_repo")
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo()
        assert evaluator.evaluate(repo) is True

    @patch("data.model.spam_detection_engine.Tag")
    def test_eval_empty_repo_false(self, mock_tag):
        mock_tag.select.return_value.where.return_value.limit.return_value.exists.return_value = (
            True
        )
        rule_view = make_rule_view("empty_repo")
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo()
        assert evaluator.evaluate(repo) is False


class TestRuleEvaluatorAccountAge:
    def test_eval_account_age_new_account(self):
        rule_view = make_rule_view("account_age", config={"max_age_hours": 24})
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo()
        namespace_user = MagicMock()
        namespace_user.creation_date = datetime.utcnow() - timedelta(hours=2)
        assert evaluator.evaluate(repo, namespace_user=namespace_user) is True

    def test_eval_account_age_old_account(self):
        rule_view = make_rule_view("account_age", config={"max_age_hours": 24})
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo()
        namespace_user = MagicMock()
        namespace_user.creation_date = datetime.utcnow() - timedelta(hours=48)
        assert evaluator.evaluate(repo, namespace_user=namespace_user) is False

    def test_eval_account_age_no_user(self):
        rule_view = make_rule_view("account_age")
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo()
        assert evaluator.evaluate(repo, namespace_user=None) is False

    def test_eval_account_age_no_creation_date(self):
        rule_view = make_rule_view("account_age")
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo()
        namespace_user = MagicMock()
        namespace_user.creation_date = None
        assert evaluator.evaluate(repo, namespace_user=namespace_user) is False


class TestRuleEvaluatorEdgeCases:
    def test_evaluator_invalid_regex(self):
        rule_view = make_rule_view("url_pattern", pattern="[invalid(")
        evaluator = RuleEvaluator(rule_view)
        assert evaluator._compiled_pattern is None
        repo = make_repo(description="anything")
        assert evaluator.evaluate(repo) is False

    def test_evaluator_unknown_type(self):
        rule_view = make_rule_view("nonexistent_type")
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo()
        assert evaluator.evaluate(repo) is False

    def test_evaluator_propagates_exceptions(self):
        rule_view = make_rule_view("keyword", pattern="test")
        evaluator = RuleEvaluator(rule_view)
        repo = MagicMock()
        repo.description = MagicMock()
        repo.description.lower = MagicMock(side_effect=RuntimeError("boom"))
        repo.id = 1
        with pytest.raises(RuntimeError, match="boom"):
            evaluator.evaluate(repo)


@pytest.fixture()
def cleanup_engine_tables(initialized_db):
    QuarantinedRepository.delete().execute()
    SpamDetectionRule.delete().execute()


class TestSpamScanner:
    def test_scanner_no_rules(self, cleanup_engine_tables):
        config = ScanConfig(scan_id="scan-no-rules", sleep_between_batches=0)
        scanner = SpamScanner(config)
        report = scanner.scan()
        assert report.total_scanned == 0
        assert report.flagged == 0
        assert report.started_at is not None
        assert report.finished_at is not None

    def test_scanner_clean_repos(self, cleanup_engine_tables):
        create_spam_detection_rule(
            name="no-match-rule",
            rule_type="keyword",
            pattern="xyznonexistentkeyword12345",
            confidence_score=80,
        )
        config = ScanConfig(scan_id="scan-clean", batch_size=200, sleep_between_batches=0)
        scanner = SpamScanner(config)
        report = scanner.scan()
        assert report.total_scanned > 0
        assert report.flagged == 0
        assert report.clean > 0

    def test_scanner_flags_matching_repos(self, cleanup_engine_tables):
        repo = get_repository("devtable", "simple")
        original_desc = repo.description
        try:
            repo.description = "spam buy cheap bitcoin"
            repo.save()

            create_spam_detection_rule(
                name="spam-keyword",
                rule_type="keyword",
                pattern="spam,bitcoin",
                confidence_score=80,
            )
            config = ScanConfig(
                scan_id="scan-flag",
                batch_size=200,
                min_confidence_threshold=50,
                dry_run=False,
                sleep_between_batches=0,
            )
            scanner = SpamScanner(config)
            report = scanner.scan()
            assert report.flagged >= 1
            assert report.total_scanned > 0

            qr = QuarantinedRepository.select().where(QuarantinedRepository.repository == repo.id)
            assert qr.exists()
        finally:
            repo.description = original_desc
            repo.save()

    def test_scanner_skips_already_flagged(self, cleanup_engine_tables):
        repo = get_repository("devtable", "simple")
        original_desc = repo.description
        try:
            repo.description = "spam buy cheap"
            repo.save()

            create_spam_detection_rule(
                name="spam-keyword",
                rule_type="keyword",
                pattern="spam,cheap",
                confidence_score=80,
            )
            create_quarantined_repo(
                repository=repo.id,
                namespace_name="devtable",
                repo_name="simple",
                original_description=original_desc,
                matched_rules=[{"rule": "pre-flagged"}],
                total_confidence=80,
                is_empty=False,
                scan_id="pre-scan",
            )

            config = ScanConfig(scan_id="scan-skip", batch_size=200, sleep_between_batches=0)
            scanner = SpamScanner(config)
            report = scanner.scan()
            assert report.skipped >= 1
            assert report.total_scanned > 0
        finally:
            repo.description = original_desc
            repo.save()

    def test_scanner_below_threshold(self, cleanup_engine_tables):
        repo = get_repository("devtable", "simple")
        original_desc = repo.description
        try:
            repo.description = "contains testword123"
            repo.save()

            create_spam_detection_rule(
                name="low-conf-rule",
                rule_type="keyword",
                pattern="testword123",
                confidence_score=10,
            )
            config = ScanConfig(
                scan_id="scan-low",
                batch_size=200,
                min_confidence_threshold=50,
                sleep_between_batches=0,
            )
            scanner = SpamScanner(config)
            report = scanner.scan()
            assert report.below_threshold >= 1
            assert report.flagged == 0
        finally:
            repo.description = original_desc
            repo.save()

    def test_scanner_error_handling(self, cleanup_engine_tables):
        create_spam_detection_rule(
            name="error-rule",
            rule_type="keyword",
            pattern="xyznonexistent12345",
            confidence_score=50,
        )
        config = ScanConfig(scan_id="scan-err", batch_size=200, sleep_between_batches=0)
        scanner = SpamScanner(config)
        with patch(
            "data.model.spam_detection_engine.RuleEvaluator.evaluate",
            side_effect=RuntimeError("db error"),
        ):
            report = scanner.scan()
        assert report.errors >= 1
        assert report.total_scanned > 0

    def test_scanner_batch_processing(self, cleanup_engine_tables):
        create_spam_detection_rule(
            name="no-match",
            rule_type="keyword",
            pattern="xyznonexistent12345",
            confidence_score=50,
        )
        config = ScanConfig(scan_id="scan-batch", batch_size=3, sleep_between_batches=0)
        scanner = SpamScanner(config)
        report = scanner.scan()
        total_repos = Repository.select().count()
        assert report.total_scanned == total_repos
        assert report.clean == total_repos

    def test_scanner_report_timestamps(self, cleanup_engine_tables):
        config = ScanConfig(scan_id="scan-ts", sleep_between_batches=0)
        scanner = SpamScanner(config)
        report = scanner.scan()
        assert isinstance(report.started_at, datetime)
        assert isinstance(report.finished_at, datetime)
        assert report.finished_at >= report.started_at

    def test_scanner_max_repos_limits_scan(self, cleanup_engine_tables):
        create_spam_detection_rule(
            name="no-match",
            rule_type="keyword",
            pattern="xyznonexistent12345",
            confidence_score=50,
        )
        total_repos = Repository.select().count()
        assert total_repos > 2

        config = ScanConfig(
            scan_id="scan-limit", batch_size=200, max_repos=2, sleep_between_batches=0
        )
        scanner = SpamScanner(config)
        report = scanner.scan()
        assert report.total_scanned == 2

    def test_scanner_max_repos_zero_means_unlimited(self, cleanup_engine_tables):
        create_spam_detection_rule(
            name="no-match",
            rule_type="keyword",
            pattern="xyznonexistent12345",
            confidence_score=50,
        )
        config = ScanConfig(
            scan_id="scan-unlimited", batch_size=200, max_repos=0, sleep_between_batches=0
        )
        scanner = SpamScanner(config)
        report = scanner.scan()
        total_repos = Repository.select().count()
        assert report.total_scanned == total_repos

    def test_scanner_prefetches_is_empty(self, cleanup_engine_tables):
        repo = get_repository("devtable", "simple")
        original_desc = repo.description
        try:
            repo.description = "spam trigger keyword xyzspamcache777"
            repo.save()

            create_spam_detection_rule(
                name="keyword-rule",
                rule_type="keyword",
                pattern="xyzspamcache777",
                confidence_score=80,
            )
            create_spam_detection_rule(
                name="empty-rule",
                rule_type="empty_repo",
                confidence_score=10,
            )
            config = ScanConfig(
                scan_id="scan-cache",
                batch_size=200,
                min_confidence_threshold=50,
                sleep_between_batches=0,
            )
            scanner = SpamScanner(config)
            report = scanner.scan()
            assert report.flagged >= 1
        finally:
            repo.description = original_desc
            repo.save()

    def test_scanner_dry_run_does_not_create_records(self, cleanup_engine_tables):
        repo = get_repository("devtable", "simple")
        original_desc = repo.description
        try:
            repo.description = "spam trigger xyzdryrunkeyword888"
            repo.save()

            create_spam_detection_rule(
                name="dryrun-rule",
                rule_type="keyword",
                pattern="xyzdryrunkeyword888",
                confidence_score=80,
            )
            config = ScanConfig(
                scan_id="scan-dryrun",
                batch_size=200,
                min_confidence_threshold=50,
                dry_run=True,
                sleep_between_batches=0,
            )
            scanner = SpamScanner(config)
            report = scanner.scan()
            assert report.flagged >= 1
            assert (
                not QuarantinedRepository.select()
                .where(QuarantinedRepository.scan_id == "scan-dryrun")
                .exists()
            )
        finally:
            repo.description = original_desc
            repo.save()

    def test_scanner_non_dry_run_creates_records(self, cleanup_engine_tables):
        repo = get_repository("devtable", "simple")
        original_desc = repo.description
        try:
            repo.description = "spam trigger xyznondryrun999"
            repo.save()

            create_spam_detection_rule(
                name="nondryrun-rule",
                rule_type="keyword",
                pattern="xyznondryrun999",
                confidence_score=80,
            )
            config = ScanConfig(
                scan_id="scan-nondryrun",
                batch_size=200,
                min_confidence_threshold=50,
                dry_run=False,
                sleep_between_batches=0,
            )
            scanner = SpamScanner(config)
            report = scanner.scan()
            assert report.flagged >= 1
            assert (
                QuarantinedRepository.select()
                .where(QuarantinedRepository.scan_id == "scan-nondryrun")
                .exists()
            )
        finally:
            repo.description = original_desc
            repo.save()


class TestScanConfigDefaults:
    def test_max_repos_default_is_zero(self):
        config = ScanConfig()
        assert config.max_repos == 0

    def test_dry_run_default_is_true(self):
        config = ScanConfig()
        assert config.dry_run is True


class TestRuleEvaluatorPropagatesErrors:
    def test_evaluator_propagates_exception(self):
        rule_view = make_rule_view("keyword", pattern="test")
        evaluator = RuleEvaluator(rule_view)
        repo = MagicMock()
        repo.description = MagicMock()
        repo.description.lower = MagicMock(side_effect=RuntimeError("boom"))
        repo.id = 1
        with pytest.raises(RuntimeError, match="boom"):
            evaluator.evaluate(repo)

    def test_evaluator_returns_false_for_unknown_type(self):
        rule_view = make_rule_view("nonexistent_type")
        evaluator = RuleEvaluator(rule_view)
        repo = make_repo()
        assert evaluator.evaluate(repo) is False


class TestRegexTimeout:
    def test_normal_regex_succeeds(self):
        import re

        pattern = re.compile(r"hello", re.IGNORECASE)
        result = _regex_search_with_timeout(pattern, "hello world", timeout=2)
        assert result is not None

    def test_no_match_returns_none(self):
        import re

        pattern = re.compile(r"xyz123", re.IGNORECASE)
        result = _regex_search_with_timeout(pattern, "hello world", timeout=2)
        assert result is None
