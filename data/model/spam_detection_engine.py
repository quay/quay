import atexit
import logging
import multiprocessing
import re
import time
import uuid as uuid_module
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from queue import Empty
from threading import Lock
from typing import Optional

from data.database import QuarantinedRepository, Repository, Tag, User
from data.model.spam import create_quarantined_repo, get_spam_detection_rules

logger = logging.getLogger(__name__)

REGEX_EVAL_TIMEOUT_SECS = 2


def _regex_worker_main(request_queue, response_queue):
    while True:
        request = request_queue.get()
        if request is None:
            return

        pattern, flags, text = request
        response_queue.put(bool(re.search(pattern, text, flags)))


class _RegexProcessEvaluator:
    def __init__(self, context=None):
        self._context = context or multiprocessing.get_context("spawn")
        self._lock = Lock()
        self._process = None
        self._request_queue = None
        self._response_queue = None

    def search(self, compiled_pattern, text, timeout=REGEX_EVAL_TIMEOUT_SECS):
        with self._lock:
            self._ensure_started_locked()
            try:
                self._request_queue.put((compiled_pattern.pattern, compiled_pattern.flags, text))
                return self._response_queue.get(timeout=timeout)
            except Empty:
                logger.warning(
                    "Regex timed out on pattern %s, restarting evaluator process",
                    compiled_pattern.pattern,
                )
                self._restart_locked()
                return None
            except Exception:
                logger.exception("Regex evaluation failed for pattern %s", compiled_pattern.pattern)
                self._restart_locked()
                return None

    def stop(self):
        with self._lock:
            self._stop_locked()

    def _ensure_started_locked(self):
        if self._process is not None and self._process.is_alive():
            return

        self._request_queue = self._context.Queue(maxsize=1)
        self._response_queue = self._context.Queue(maxsize=1)
        self._process = self._context.Process(
            target=_regex_worker_main,
            args=(self._request_queue, self._response_queue),
            daemon=True,
        )
        self._process.start()

    def _restart_locked(self):
        self._stop_locked()
        self._ensure_started_locked()

    def _stop_locked(self):
        if self._process is not None:
            if self._process.is_alive():
                self._process.terminate()
            self._process.join(timeout=1)
            if self._process.is_alive():
                self._process.kill()
                self._process.join(timeout=1)

        for queue_obj in (self._request_queue, self._response_queue):
            if queue_obj is not None:
                queue_obj.cancel_join_thread()
                queue_obj.close()

        self._process = None
        self._request_queue = None
        self._response_queue = None


_regex_evaluator = _RegexProcessEvaluator()
atexit.register(_regex_evaluator.stop)


def _regex_search_with_timeout(compiled_pattern, text, timeout=REGEX_EVAL_TIMEOUT_SECS):
    return _regex_evaluator.search(compiled_pattern, text, timeout=timeout)


@dataclass
class ScanConfig:
    batch_size: int = 200
    sleep_between_batches: float = 0.5
    min_confidence_threshold: int = 50
    dry_run: bool = True
    max_repos: int = 0
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
        handler = getattr(self, f"_eval_{self.rule.rule_type}", None)
        if handler:
            return handler(repo, namespace_user)
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
        return bool(_regex_search_with_timeout(self._compiled_pattern, repo.description))

    def _eval_repo_name_pattern(self, repo, namespace_user):
        if not self._compiled_pattern:
            return False
        return bool(_regex_search_with_timeout(self._compiled_pattern, repo.name))

    def _eval_empty_repo(self, repo, namespace_user):
        if hasattr(repo, "_prefetched_is_empty"):
            return repo._prefetched_is_empty
        is_empty = not (
            Tag.select()
            .where(Tag.repository == repo.id, Tag.lifetime_end_ms >> None)
            .limit(1)
            .exists()
        )
        return is_empty

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
        last_seen_id = 0

        while True:
            if self.config.max_repos > 0 and self.report.total_scanned >= self.config.max_repos:
                break

            repos = list(
                Repository.select(Repository, User)
                .join(User, on=(Repository.namespace_user == User.id))
                .where(Repository.id > last_seen_id)
                .order_by(Repository.id)
                .limit(self.config.batch_size)
            )

            if not repos:
                break

            repo_ids = [r.id for r in repos]
            already_flagged_ids = set(
                row[0]
                for row in QuarantinedRepository.select(QuarantinedRepository.repository)
                .where(
                    QuarantinedRepository.repository.in_(repo_ids),
                    QuarantinedRepository.status.in_(["flagged", "quarantined"]),
                )
                .tuples()
            )

            non_empty_ids = set(
                row[0]
                for row in Tag.select(Tag.repository)
                .where(Tag.repository.in_(repo_ids), Tag.lifetime_end_ms >> None)
                .distinct()
                .tuples()
            )
            for repo in repos:
                repo._prefetched_is_empty = repo.id not in non_empty_ids

            for repo in repos:
                last_seen_id = repo.id

                if self.config.max_repos > 0 and self.report.total_scanned >= self.config.max_repos:
                    break

                self.report.total_scanned += 1
                try:
                    if repo.id in already_flagged_ids:
                        self.report.skipped += 1
                        continue

                    namespace_user = repo.namespace_user
                    matches = []
                    for evaluator in evaluators:
                        if evaluator.evaluate(repo, namespace_user):
                            matches.append(
                                RuleMatch(
                                    rule_uuid=evaluator.rule.uuid,
                                    rule_name=evaluator.rule.name,
                                    rule_type=evaluator.rule.rule_type,
                                    confidence=evaluator.rule.confidence_score,
                                )
                            )

                    if not matches:
                        self.report.clean += 1
                        continue

                    total_confidence = min(100, sum(m.confidence for m in matches))
                    if total_confidence < self.config.min_confidence_threshold:
                        self.report.below_threshold += 1
                        continue

                    is_empty = repo._prefetched_is_empty

                    matched_rules_data = [
                        {
                            "rule_uuid": m.rule_uuid,
                            "rule_name": m.rule_name,
                            "rule_type": m.rule_type,
                            "confidence": m.confidence,
                        }
                        for m in matches
                    ]

                    if not self.config.dry_run:
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
                        namespace_user.username,
                        repo.name,
                        total_confidence,
                        len(matches),
                    )
                except Exception:
                    self.report.errors += 1
                    logger.exception("Error processing repo %s", repo.id)

            if self.config.sleep_between_batches > 0:
                time.sleep(self.config.sleep_between_batches)

        self.report.finished_at = datetime.utcnow()
        return self.report
