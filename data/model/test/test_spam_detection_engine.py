import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from data.model.spam_detection_engine import (
    RuleEvaluator,
    RuleMatch,
    ScanConfig,
    ScanReport,
    SpamScanner,
)


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
    repo = MagicMock()
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

    def test_evaluator_exception_handling(self):
        rule_view = make_rule_view("keyword", pattern="test")
        evaluator = RuleEvaluator(rule_view)
        repo = MagicMock()
        repo.description = MagicMock()
        repo.description.lower = MagicMock(side_effect=RuntimeError("boom"))
        repo.id = 1
        assert evaluator.evaluate(repo) is False


def _setup_repo_mock(mock_repo, batches, max_id=1):
    batch_idx = [0]

    def select_side_effect(*args, **kwargs):
        join_mock = MagicMock()

        def where_side_effect(*args, **kwargs):
            order_mock = MagicMock()
            if batch_idx[0] < len(batches):
                batch = batches[batch_idx[0]]
                order_mock.__iter__ = lambda self, b=batch: iter(b)
                batch_idx[0] += 1
            else:
                order_mock.__iter__ = lambda self: iter([])
            return order_mock

        join_mock.where = where_side_effect
        result = MagicMock()
        result.join.return_value = join_mock

        max_id_mock = MagicMock()
        max_id_entry = MagicMock()
        max_id_entry.id = max_id
        max_id_mock.limit.return_value = [max_id_entry]
        result.order_by.return_value = max_id_mock
        return result

    mock_repo.select.side_effect = select_side_effect


@patch("data.model.spam_detection_engine.time")
@patch("data.model.spam_detection_engine.Tag")
@patch("data.model.spam_detection_engine.Repository")
@patch("data.model.spam_detection_engine.create_quarantined_repo")
@patch("data.model.spam_detection_engine.repo_already_flagged")
@patch("data.model.spam_detection_engine.get_spam_detection_rules")
class TestSpamScanner:
    def test_scanner_no_rules(
        self, mock_get_rules, mock_flagged, mock_create, mock_repo, mock_tag, mock_time
    ):
        mock_get_rules.return_value = []
        config = ScanConfig(scan_id="scan-no-rules")
        scanner = SpamScanner(config)
        report = scanner.scan()
        assert report.total_scanned == 0
        assert report.flagged == 0
        assert report.started_at is not None
        assert report.finished_at is not None

    def test_scanner_clean_repos(
        self, mock_get_rules, mock_flagged, mock_create, mock_repo, mock_tag, mock_time
    ):
        rule = make_rule_view("keyword", pattern="spam")
        mock_get_rules.return_value = [rule]
        mock_flagged.return_value = False

        repo = make_repo(name="clean-repo", description="a normal repo", repo_id=1)
        repo.namespace_user = MagicMock()
        repo.namespace_user.username = "testuser"

        _setup_repo_mock(mock_repo, [[repo]], max_id=1)

        config = ScanConfig(scan_id="scan-clean", batch_size=200, sleep_between_batches=0)
        scanner = SpamScanner(config)
        report = scanner.scan()
        assert report.clean == 1
        assert report.flagged == 0
        assert report.total_scanned == 1

    def test_scanner_skips_already_flagged(
        self, mock_get_rules, mock_flagged, mock_create, mock_repo, mock_tag, mock_time
    ):
        rule = make_rule_view("keyword", pattern="spam")
        mock_get_rules.return_value = [rule]
        mock_flagged.return_value = True

        repo = make_repo(repo_id=1)
        repo.namespace_user = MagicMock()

        _setup_repo_mock(mock_repo, [[repo]], max_id=1)

        config = ScanConfig(scan_id="scan-skip", batch_size=200, sleep_between_batches=0)
        scanner = SpamScanner(config)
        report = scanner.scan()
        assert report.skipped == 1
        assert report.flagged == 0
        assert report.total_scanned == 1

    def test_scanner_flags_matching_repos(
        self, mock_get_rules, mock_flagged, mock_create, mock_repo, mock_tag, mock_time
    ):
        rule = make_rule_view("keyword", pattern="spam", confidence_score=80)
        mock_get_rules.return_value = [rule]
        mock_flagged.return_value = False

        repo = make_repo(name="spam-repo", description="spam content here", repo_id=1)
        namespace_user = MagicMock()
        namespace_user.username = "spammer"
        repo.namespace_user = namespace_user

        _setup_repo_mock(mock_repo, [[repo]], max_id=1)

        mock_tag.select.return_value.where.return_value.limit.return_value.exists.return_value = (
            False
        )

        config = ScanConfig(
            scan_id="scan-flag",
            batch_size=200,
            min_confidence_threshold=50,
            sleep_between_batches=0,
        )
        scanner = SpamScanner(config)
        report = scanner.scan()
        assert report.flagged == 1
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args
        assert call_kwargs[1]["repository"] == 1
        assert call_kwargs[1]["total_confidence"] == 80
        assert call_kwargs[1]["is_empty"] is True

    def test_scanner_below_threshold(
        self, mock_get_rules, mock_flagged, mock_create, mock_repo, mock_tag, mock_time
    ):
        rule = make_rule_view("keyword", pattern="test", confidence_score=20)
        mock_get_rules.return_value = [rule]
        mock_flagged.return_value = False

        repo = make_repo(name="low-conf", description="test content", repo_id=1)
        repo.namespace_user = MagicMock()

        _setup_repo_mock(mock_repo, [[repo]], max_id=1)

        config = ScanConfig(
            scan_id="scan-low", batch_size=200, min_confidence_threshold=50, sleep_between_batches=0
        )
        scanner = SpamScanner(config)
        report = scanner.scan()
        assert report.below_threshold == 1
        assert report.flagged == 0
        mock_create.assert_not_called()

    def test_scanner_error_handling(
        self, mock_get_rules, mock_flagged, mock_create, mock_repo, mock_tag, mock_time
    ):
        rule = make_rule_view("keyword", pattern="test")
        mock_get_rules.return_value = [rule]
        mock_flagged.side_effect = RuntimeError("db error")

        repo = make_repo(repo_id=1)
        repo.namespace_user = MagicMock()

        _setup_repo_mock(mock_repo, [[repo]], max_id=1)

        config = ScanConfig(scan_id="scan-err", batch_size=200, sleep_between_batches=0)
        scanner = SpamScanner(config)
        report = scanner.scan()
        assert report.errors == 1
        assert report.total_scanned == 1

    def test_scanner_batch_processing(
        self, mock_get_rules, mock_flagged, mock_create, mock_repo, mock_tag, mock_time
    ):
        rule = make_rule_view("keyword", pattern="nomatch")
        mock_get_rules.return_value = [rule]
        mock_flagged.return_value = False

        repo1 = make_repo(name="repo1", description="clean", repo_id=1)
        repo1.namespace_user = MagicMock()
        repo2 = make_repo(name="repo2", description="clean", repo_id=201)
        repo2.namespace_user = MagicMock()

        _setup_repo_mock(mock_repo, [[repo1], [repo2]], max_id=201)

        config = ScanConfig(scan_id="scan-batch", batch_size=200, sleep_between_batches=0)
        scanner = SpamScanner(config)
        report = scanner.scan()
        assert report.total_scanned == 2
        assert report.clean == 2

    def test_scanner_report_timestamps(
        self, mock_get_rules, mock_flagged, mock_create, mock_repo, mock_tag, mock_time
    ):
        mock_get_rules.return_value = []
        config = ScanConfig(scan_id="scan-ts")
        scanner = SpamScanner(config)
        report = scanner.scan()
        assert isinstance(report.started_at, datetime)
        assert isinstance(report.finished_at, datetime)
        assert report.finished_at >= report.started_at
