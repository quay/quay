import logging
import re
from datetime import datetime

from data.database import QuarantinedRepository, Repository, SpamDetectionRule, User
from data.model import DataModelException, db_transaction
from data.model import log as logs_model
from data.model import notification as notification_model

logger = logging.getLogger(__name__)

VALID_RULE_TYPES = {"keyword", "url_pattern", "repo_name_pattern", "empty_repo", "account_age"}
VALID_STATUSES = {"flagged", "quarantined", "restored", "dismissed"}


class InvalidSpamDetectionRule(DataModelException):
    pass


class SpamDetectionRuleNotFound(DataModelException):
    pass


class QuarantinedRepoNotFound(DataModelException):
    pass


class SpamDetectionRuleView:
    def __init__(self, db_row):
        self._db_row = db_row
        self.uuid = db_row.uuid
        self.name = db_row.name
        self.rule_type = db_row.rule_type
        self.pattern = db_row.pattern
        self.config = db_row.config or {}
        self.confidence_score = db_row.confidence_score
        self.enabled = db_row.enabled
        self.created_at = db_row.created_at
        self.updated_at = db_row.updated_at

    def get_view(self):
        return {
            "uuid": self.uuid,
            "name": self.name,
            "rule_type": self.rule_type,
            "pattern": self.pattern,
            "config": self.config,
            "confidence_score": self.confidence_score,
            "enabled": self.enabled,
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None,
        }


class QuarantinedRepoView:
    def __init__(self, db_row):
        self._db_row = db_row
        self.uuid = db_row.uuid
        self.repository_id = db_row.repository_id
        self.namespace_name = db_row.namespace_name
        self.repository_name = db_row.repository_name
        self.status = db_row.status
        self.original_description = db_row.original_description
        self.matched_rules = db_row.matched_rules or []
        self.total_confidence_score = db_row.total_confidence_score
        self.is_empty = db_row.is_empty
        self.scan_id = db_row.scan_id
        self.actioned_by = db_row.actioned_by
        self.actioned_at = db_row.actioned_at
        self.created_at = db_row.created_at
        self.updated_at = db_row.updated_at

    def get_view(self):
        return {
            "uuid": self.uuid,
            "namespace_name": self.namespace_name,
            "repository_name": self.repository_name,
            "status": self.status,
            "original_description": self.original_description,
            "matched_rules": self.matched_rules,
            "total_confidence_score": self.total_confidence_score,
            "is_empty": self.is_empty,
            "scan_id": self.scan_id,
            "actioned_by": self.actioned_by,
            "actioned_at": str(self.actioned_at) if self.actioned_at else None,
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None,
        }


def validate_spam_rule(rule_type, pattern=None, confidence_score=50):
    if rule_type not in VALID_RULE_TYPES:
        raise InvalidSpamDetectionRule(
            f"Invalid rule_type: {rule_type}. Must be one of: {', '.join(sorted(VALID_RULE_TYPES))}"
        )

    if not isinstance(confidence_score, int) or confidence_score < 0 or confidence_score > 100:
        raise InvalidSpamDetectionRule("confidence_score must be an integer between 0 and 100")

    if rule_type in ("url_pattern", "repo_name_pattern"):
        if not pattern:
            raise InvalidSpamDetectionRule(f"pattern is required for rule type '{rule_type}'")
        try:
            re.compile(pattern)
        except re.error as e:
            raise InvalidSpamDetectionRule(f"Invalid regex pattern: {e}")


def get_spam_detection_rules(enabled_only=False):
    query = SpamDetectionRule.select()
    if enabled_only:
        query = query.where(SpamDetectionRule.enabled == True)
    return [SpamDetectionRuleView(row) for row in query]


def get_spam_detection_rule_by_uuid(uuid):
    try:
        row = SpamDetectionRule.select().where(SpamDetectionRule.uuid == uuid).get()
        return SpamDetectionRuleView(row)
    except SpamDetectionRule.DoesNotExist:
        return None


def create_spam_detection_rule(name, rule_type, pattern=None, config=None, confidence_score=50):
    validate_spam_rule(rule_type, pattern, confidence_score)
    with db_transaction():
        row = SpamDetectionRule.create(
            name=name,
            rule_type=rule_type,
            pattern=pattern,
            config=config or {},
            confidence_score=confidence_score,
        )
        return SpamDetectionRuleView(row)


def update_spam_detection_rule(uuid, **fields):
    rule = get_spam_detection_rule_by_uuid(uuid)
    if not rule:
        raise SpamDetectionRuleNotFound(f"Rule {uuid} not found")

    rule_type = fields.get("rule_type", rule.rule_type)
    pattern = fields.get("pattern", rule.pattern)
    confidence_score = fields.get("confidence_score", rule.confidence_score)
    validate_spam_rule(rule_type, pattern, confidence_score)

    update_fields = {}
    allowed = {"name", "rule_type", "pattern", "config", "confidence_score", "enabled"}
    for key, value in fields.items():
        if key in allowed:
            update_fields[getattr(SpamDetectionRule, key)] = value

    if not update_fields:
        return True

    update_fields[SpamDetectionRule.updated_at] = datetime.utcnow()

    with db_transaction():
        SpamDetectionRule.update(update_fields).where(SpamDetectionRule.uuid == uuid).execute()
    return True


def delete_spam_detection_rule(uuid):
    rule = get_spam_detection_rule_by_uuid(uuid)
    if not rule:
        raise SpamDetectionRuleNotFound(f"Rule {uuid} not found")
    with db_transaction():
        SpamDetectionRule.delete().where(SpamDetectionRule.uuid == uuid).execute()
    return True


def _lookup_performer(username):
    return User.get_or_none(User.username == username) if username else None


def _log_quarantined_repo_action(kind_name, qr, repo, actioned_by):
    logs_model.log_action(
        kind_name,
        qr.namespace_name,
        performer=_lookup_performer(actioned_by),
        repository=repo,
        metadata={
            "repo": qr.repository_name,
            "namespace": qr.namespace_name,
            "quarantined_repo_uuid": qr.uuid,
            "status": qr.status,
        },
    )


def _quarantined_repo_page_filter(page_token):
    if not page_token:
        return None

    last_score = page_token.get("last_score")
    last_id = page_token.get("last_id")
    if last_score is None or last_id is None:
        return None

    return (QuarantinedRepository.total_confidence_score < last_score) | (
        (QuarantinedRepository.total_confidence_score == last_score)
        & (QuarantinedRepository.id < last_id)
    )


def get_quarantined_repos(
    status=None, min_confidence=0, namespace=None, scan_id=None, page_token=None, limit=50
):
    query = QuarantinedRepository.select()

    if status:
        query = query.where(QuarantinedRepository.status == status)
    if min_confidence > 0:
        query = query.where(QuarantinedRepository.total_confidence_score >= min_confidence)
    if namespace:
        query = query.where(QuarantinedRepository.namespace_name == namespace)
    if scan_id:
        query = query.where(QuarantinedRepository.scan_id == scan_id)

    page_filter = _quarantined_repo_page_filter(page_token)
    if page_filter is not None:
        query = query.where(page_filter)

    results = list(
        query.order_by(
            QuarantinedRepository.total_confidence_score.desc(),
            QuarantinedRepository.id.desc(),
        ).limit(limit + 1)
    )

    next_token = None
    if len(results) > limit:
        next_row = results[limit - 1]
        next_token = {
            "last_score": next_row.total_confidence_score,
            "last_id": next_row.id,
        }
        results = results[:limit]

    return [QuarantinedRepoView(row) for row in results], next_token


def get_quarantined_repo_by_uuid(uuid):
    try:
        row = QuarantinedRepository.select().where(QuarantinedRepository.uuid == uuid).get()
        return QuarantinedRepoView(row)
    except QuarantinedRepository.DoesNotExist:
        return None


def create_quarantined_repo(
    repository,
    namespace_name,
    repo_name,
    original_description,
    matched_rules,
    total_confidence,
    is_empty,
    scan_id,
):
    with db_transaction():
        row = QuarantinedRepository.create(
            repository=repository,
            namespace_name=namespace_name,
            repository_name=repo_name,
            original_description=original_description,
            matched_rules=matched_rules,
            total_confidence_score=total_confidence,
            is_empty=is_empty,
            scan_id=scan_id,
        )
        return QuarantinedRepoView(row)


def repo_already_flagged(repository_id):
    return (
        QuarantinedRepository.select()
        .where(
            QuarantinedRepository.repository == repository_id,
            QuarantinedRepository.status.in_(["flagged", "quarantined"]),
        )
        .exists()
    )


class InvalidStatusTransition(DataModelException):
    pass


def quarantine_repository(uuid, actioned_by):
    with db_transaction():
        try:
            qr = QuarantinedRepository.select().where(QuarantinedRepository.uuid == uuid).get()
        except QuarantinedRepository.DoesNotExist:
            raise QuarantinedRepoNotFound(f"Quarantined repo {uuid} not found")

        if qr.status != "flagged":
            raise InvalidStatusTransition(
                f"Cannot quarantine repo with status '{qr.status}' (must be 'flagged')"
            )

        now = datetime.utcnow()
        repo = Repository.select().where(Repository.id == qr.repository_id).get()
        Repository.update(description=None).where(Repository.id == qr.repository_id).execute()
        QuarantinedRepository.update(
            status="quarantined",
            actioned_by=actioned_by,
            actioned_at=now,
            updated_at=now,
        ).where(QuarantinedRepository.uuid == uuid).execute()
        qr.status = "quarantined"
        qr.actioned_by = actioned_by
        qr.actioned_at = now
        qr.updated_at = now
        _log_quarantined_repo_action("spam_repo_quarantined", qr, repo, actioned_by)

    try:
        owner = User.select().where(User.id == repo.namespace_user_id).get()
        notification_model.create_notification(
            "repo_spam_quarantined",
            owner,
            metadata={
                "repo": qr.repository_name,
                "namespace": qr.namespace_name,
            },
        )
    except Exception:
        logger.exception("Failed to notify owner of quarantined repo %s", uuid)

    return True


def restore_repository(uuid, actioned_by):
    with db_transaction():
        try:
            qr = QuarantinedRepository.select().where(QuarantinedRepository.uuid == uuid).get()
        except QuarantinedRepository.DoesNotExist:
            raise QuarantinedRepoNotFound(f"Quarantined repo {uuid} not found")

        if qr.status != "quarantined":
            raise InvalidStatusTransition(
                f"Cannot restore repo with status '{qr.status}' (must be 'quarantined')"
            )

        now = datetime.utcnow()
        repo = Repository.select().where(Repository.id == qr.repository_id).get()
        Repository.update(description=qr.original_description).where(
            Repository.id == qr.repository_id
        ).execute()
        QuarantinedRepository.update(
            status="restored",
            actioned_by=actioned_by,
            actioned_at=now,
            updated_at=now,
        ).where(QuarantinedRepository.uuid == uuid).execute()
        qr.status = "restored"
        qr.actioned_by = actioned_by
        qr.actioned_at = now
        qr.updated_at = now
        _log_quarantined_repo_action("spam_repo_restored", qr, repo, actioned_by)
    return True


def dismiss_quarantined_repo(uuid, actioned_by):
    with db_transaction():
        try:
            qr = QuarantinedRepository.select().where(QuarantinedRepository.uuid == uuid).get()
        except QuarantinedRepository.DoesNotExist:
            raise QuarantinedRepoNotFound(f"Quarantined repo {uuid} not found")

        if qr.status not in ("flagged", "quarantined"):
            raise InvalidStatusTransition(
                f"Cannot dismiss repo with status '{qr.status}' (must be 'flagged' or 'quarantined')"
            )

        now = datetime.utcnow()
        repo = Repository.select().where(Repository.id == qr.repository_id).get()
        QuarantinedRepository.update(
            status="dismissed",
            actioned_by=actioned_by,
            actioned_at=now,
            updated_at=now,
        ).where(QuarantinedRepository.uuid == uuid).execute()
        qr.status = "dismissed"
        qr.actioned_by = actioned_by
        qr.actioned_at = now
        qr.updated_at = now
        _log_quarantined_repo_action("spam_repo_dismissed", qr, repo, actioned_by)
    return True
