import logging
import re
import time
import uuid as uuid_module
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from data.database import Repository, Tag, User, db_transaction
from data.model.spam import (
    create_quarantined_repo,
    get_spam_detection_rules,
    repo_already_flagged,
)

logger = logging.getLogger(__name__)


@dataclass
class ScanConfig:
    batch_size: int = 200
    sleep_between_batches: float = 0.5
    min_confidence_threshold: int = 50
    dry_run: bool = True
    scan_id: str = field(default_factory=lambda: str(uuid_module.uuid4()))


@dataclass
class RuleMatch:
    rule_uuid: str
    rule_name: str
    rule_type: str
    confidence: int


@dataclass
class ScanReport:
    scan_id: str
    total_scanned: int = 0
    flagged: int = 0
    skipped: int = 0
    clean: int = 0
    below_threshold: int = 0
    errors: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    def to_dict(self):
        return {
            "scan_id": self.scan_id,
            "total_scanned": self.total_scanned,
            "flagged": self.flagged,
            "skipped": self.skipped,
            "clean": self.clean,
            "below_threshold": self.below_threshold,
            "errors": self.errors,
            "started_at": str(self.started_at) if self.started_at else None,
            "finished_at": str(self.finished_at) if self.finished_at else None,
        }


class RuleEvaluator:
    def __init__(self, rule_view):
        self.rule = rule_view
        self._compiled_pattern = None
        if rule_view.rule_type in ("url_pattern", "repo_name_pattern") and rule_view.pattern:
            try:
                self._compiled_pattern = re.compile(rule_view.pattern, re.IGNORECASE)
            except re.error:
                logger.warning("Invalid regex in rule %s: %s", rule_view.uuid, rule_view.pattern)

    def evaluate(self, repo, namespace_user=None):
        try:
            handler = getattr(self, f"_eval_{self.rule.rule_type}", None)
            if handler:
                return handler(repo, namespace_user)
        except Exception:
            logger.exception("Error evaluating rule %s on repo %s", self.rule.uuid, repo.id)
        return False

    def _eval_keyword(self, repo, namespace_user):
        if not repo.description or not self.rule.pattern:
            return False
        keywords = [k.strip().lower() for k in self.rule.pattern.split(",") if k.strip()]
        desc_lower = repo.description.lower()
        return any(kw in desc_lower for kw in keywords)

    def _eval_url_pattern(self, repo, namespace_user):
        if not repo.description or not self._compiled_pattern:
            return False
        return bool(self._compiled_pattern.search(repo.description))

    def _eval_repo_name_pattern(self, repo, namespace_user):
        if not self._compiled_pattern:
            return False
        return bool(self._compiled_pattern.search(repo.name))

    def _eval_empty_repo(self, repo, namespace_user):
        return not (
            Tag.select()
            .where(Tag.repository == repo.id, Tag.lifetime_end_ms >> None)
            .limit(1)
            .exists()
        )

    def _eval_account_age(self, repo, namespace_user):
        if not namespace_user or not namespace_user.creation_date:
            return False
        config = self.rule.config or {}
        max_age_hours = config.get("max_age_hours", 24)
        threshold = datetime.utcnow() - timedelta(hours=max_age_hours)
        return namespace_user.creation_date > threshold


class SpamScanner:
    def __init__(self, config: ScanConfig):
        self.config = config
        self.report = ScanReport(scan_id=config.scan_id)

    def scan(self):
        self.report.started_at = datetime.utcnow()
        rules = get_spam_detection_rules(enabled_only=True)
        if not rules:
            logger.info("No enabled spam detection rules, skipping scan")
            self.report.finished_at = datetime.utcnow()
            return self.report

        evaluators = [RuleEvaluator(r) for r in rules]
        cursor = 0

        while True:
            repos = list(
                Repository.select(Repository, User)
                .join(User, on=(Repository.namespace_user == User.id))
                .where(Repository.id >= cursor, Repository.id < cursor + self.config.batch_size)
                .order_by(Repository.id)
            )

            if not repos:
                max_id = Repository.select(Repository.id).order_by(Repository.id.desc()).limit(1)
                max_id_list = list(max_id)
                if not max_id_list or cursor >= max_id_list[0].id:
                    break
                cursor += self.config.batch_size
                continue

            for repo in repos:
                self.report.total_scanned += 1
                try:
                    if repo_already_flagged(repo.id):
                        self.report.skipped += 1
                        continue

                    namespace_user = repo.namespace_user
                    matches = []
                    for evaluator in evaluators:
                        if evaluator.evaluate(repo, namespace_user):
                            matches.append(RuleMatch(
                                rule_uuid=evaluator.rule.uuid,
                                rule_name=evaluator.rule.name,
                                rule_type=evaluator.rule.rule_type,
                                confidence=evaluator.rule.confidence_score,
                            ))

                    if not matches:
                        self.report.clean += 1
                        continue

                    total_confidence = min(100, sum(m.confidence for m in matches))
                    if total_confidence < self.config.min_confidence_threshold:
                        self.report.below_threshold += 1
                        continue

                    is_empty = not (
                        Tag.select()
                        .where(Tag.repository == repo.id, Tag.lifetime_end_ms >> None)
                        .limit(1)
                        .exists()
                    )

                    matched_rules_data = [
                        {
                            "rule_uuid": m.rule_uuid,
                            "rule_name": m.rule_name,
                            "rule_type": m.rule_type,
                            "confidence": m.confidence,
                        }
                        for m in matches
                    ]

                    create_quarantined_repo(
                        repository=repo.id,
                        namespace_name=namespace_user.username,
                        repo_name=repo.name,
                        original_description=repo.description,
                        matched_rules=matched_rules_data,
                        total_confidence=total_confidence,
                        is_empty=is_empty,
                        scan_id=self.config.scan_id,
                    )
                    self.report.flagged += 1
                    logger.debug(
                        "Flagged repo %s/%s (confidence: %d, rules: %d)",
                        namespace_user.username, repo.name, total_confidence, len(matches),
                    )
                except Exception:
                    self.report.errors += 1
                    logger.exception("Error processing repo %s", repo.id)

            cursor += self.config.batch_size
            if self.config.sleep_between_batches > 0:
                time.sleep(self.config.sleep_between_batches)

        self.report.finished_at = datetime.utcnow()
        return self.report
