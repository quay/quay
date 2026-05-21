import logging

from flask import request

import features
from auth import scopes
from auth.auth_context import get_authenticated_user
from auth.permissions import SuperUserPermission
from data.model import spam
from endpoints.api import (
    ApiResource,
    InvalidRequest,
    NotFound,
    Unauthorized,
    allow_if_any_superuser,
    internal_only,
    nickname,
    parse_args,
    query_param,
    require_fresh_login,
    require_scope,
    resource,
    show_if,
    validate_json_request,
    verify_not_prod,
)

logger = logging.getLogger(__name__)


@resource("/v1/superuser/spam/rules")
@internal_only
@show_if(features.SUPER_USERS)
@show_if(features.SPAM_DETECTION)
class SuperUserSpamRuleList(ApiResource):
    schemas = {
        "SpamDetectionRule": {
            "type": "object",
            "required": ["name", "rule_type"],
            "properties": {
                "name": {"type": "string"},
                "rule_type": {"type": "string"},
                "pattern": {"type": "string"},
                "config": {"type": "object"},
                "confidence_score": {"type": "integer"},
                "enabled": {"type": "boolean"},
            },
        },
    }

    @require_fresh_login
    @verify_not_prod
    @nickname("listSpamDetectionRules")
    @require_scope(scopes.SUPERUSER)
    def get(self):
        if not allow_if_any_superuser():
            raise Unauthorized()
        rules = spam.get_spam_detection_rules()
        return {"rules": [r.get_view() for r in rules]}

    @require_fresh_login
    @verify_not_prod
    @nickname("createSpamDetectionRule")
    @require_scope(scopes.SUPERUSER)
    @validate_json_request("SpamDetectionRule")
    def post(self):
        if not SuperUserPermission().can():
            raise Unauthorized()
        data = request.get_json()
        try:
            rule = spam.create_spam_detection_rule(
                name=data["name"],
                rule_type=data["rule_type"],
                pattern=data.get("pattern"),
                config=data.get("config"),
                confidence_score=data.get("confidence_score", 50),
            )
            return rule.get_view(), 201
        except spam.InvalidSpamDetectionRule as e:
            raise InvalidRequest(str(e))


@resource("/v1/superuser/spam/rules/<rule_uuid>")
@internal_only
@show_if(features.SUPER_USERS)
@show_if(features.SPAM_DETECTION)
class SuperUserSpamRuleDetail(ApiResource):
    schemas = {
        "UpdateSpamDetectionRule": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "rule_type": {"type": "string"},
                "pattern": {"type": "string"},
                "config": {"type": "object"},
                "confidence_score": {"type": "integer"},
                "enabled": {"type": "boolean"},
            },
        },
    }

    @require_fresh_login
    @verify_not_prod
    @nickname("getSpamDetectionRule")
    @require_scope(scopes.SUPERUSER)
    def get(self, rule_uuid):
        if not allow_if_any_superuser():
            raise Unauthorized()
        rule = spam.get_spam_detection_rule_by_uuid(rule_uuid)
        if not rule:
            raise NotFound()
        return rule.get_view()

    @require_fresh_login
    @verify_not_prod
    @nickname("updateSpamDetectionRule")
    @require_scope(scopes.SUPERUSER)
    @validate_json_request("UpdateSpamDetectionRule")
    def put(self, rule_uuid):
        if not SuperUserPermission().can():
            raise Unauthorized()
        data = request.get_json()
        try:
            spam.update_spam_detection_rule(rule_uuid, **data)
            rule = spam.get_spam_detection_rule_by_uuid(rule_uuid)
            return rule.get_view()
        except spam.SpamDetectionRuleNotFound:
            raise NotFound()
        except spam.InvalidSpamDetectionRule as e:
            raise InvalidRequest(str(e))

    @require_fresh_login
    @verify_not_prod
    @nickname("deleteSpamDetectionRule")
    @require_scope(scopes.SUPERUSER)
    def delete(self, rule_uuid):
        if not SuperUserPermission().can():
            raise Unauthorized()
        try:
            spam.delete_spam_detection_rule(rule_uuid)
            return "", 204
        except spam.SpamDetectionRuleNotFound:
            raise NotFound()


@resource("/v1/superuser/spam/flagged")
@internal_only
@show_if(features.SUPER_USERS)
@show_if(features.SPAM_DETECTION)
class SuperUserFlaggedRepoList(ApiResource):
    @require_fresh_login
    @verify_not_prod
    @nickname("listFlaggedRepos")
    @require_scope(scopes.SUPERUSER)
    @parse_args()
    @query_param("status", "Filter by status", type=str)
    @query_param("min_confidence", "Minimum confidence score", type=int, default=0)
    @query_param("namespace", "Filter by namespace", type=str)
    @query_param("scan_id", "Filter by scan ID", type=str)
    @query_param("page_token", "Pagination token", type=str)
    @query_param("limit", "Results per page", type=int, default=50)
    def get(self, parsed_args):
        if not allow_if_any_superuser():
            raise Unauthorized()
        repos, next_token = spam.get_quarantined_repos(
            status=parsed_args.get("status"),
            min_confidence=parsed_args.get("min_confidence", 0),
            namespace=parsed_args.get("namespace"),
            scan_id=parsed_args.get("scan_id"),
            page_token=parsed_args.get("page_token"),
            limit=min(parsed_args.get("limit", 50), 100),
        )
        result = {"flagged_repos": [r.get_view() for r in repos]}
        if next_token:
            result["next_page_token"] = next_token
        return result


@resource("/v1/superuser/spam/flagged/<repo_uuid>")
@internal_only
@show_if(features.SUPER_USERS)
@show_if(features.SPAM_DETECTION)
class SuperUserFlaggedRepoDetail(ApiResource):
    @require_fresh_login
    @verify_not_prod
    @nickname("getFlaggedRepo")
    @require_scope(scopes.SUPERUSER)
    def get(self, repo_uuid):
        if not allow_if_any_superuser():
            raise Unauthorized()
        repo = spam.get_quarantined_repo_by_uuid(repo_uuid)
        if not repo:
            raise NotFound()
        return repo.get_view()


@resource("/v1/superuser/spam/flagged/<repo_uuid>/quarantine")
@internal_only
@show_if(features.SUPER_USERS)
@show_if(features.SPAM_DETECTION)
class SuperUserQuarantineRepo(ApiResource):
    @require_fresh_login
    @verify_not_prod
    @nickname("quarantineRepo")
    @require_scope(scopes.SUPERUSER)
    def post(self, repo_uuid):
        if not SuperUserPermission().can():
            raise Unauthorized()
        try:
            user = get_authenticated_user()
            spam.quarantine_repository(repo_uuid, user.username if user else "superuser")
            return {"status": "quarantined"}
        except spam.QuarantinedRepoNotFound:
            raise NotFound()


@resource("/v1/superuser/spam/flagged/<repo_uuid>/restore")
@internal_only
@show_if(features.SUPER_USERS)
@show_if(features.SPAM_DETECTION)
class SuperUserRestoreRepo(ApiResource):
    @require_fresh_login
    @verify_not_prod
    @nickname("restoreRepo")
    @require_scope(scopes.SUPERUSER)
    def post(self, repo_uuid):
        if not SuperUserPermission().can():
            raise Unauthorized()
        try:
            user = get_authenticated_user()
            spam.restore_repository(repo_uuid, user.username if user else "superuser")
            return {"status": "restored"}
        except spam.QuarantinedRepoNotFound:
            raise NotFound()


@resource("/v1/superuser/spam/flagged/<repo_uuid>/dismiss")
@internal_only
@show_if(features.SUPER_USERS)
@show_if(features.SPAM_DETECTION)
class SuperUserDismissRepo(ApiResource):
    @require_fresh_login
    @verify_not_prod
    @nickname("dismissRepo")
    @require_scope(scopes.SUPERUSER)
    def post(self, repo_uuid):
        if not SuperUserPermission().can():
            raise Unauthorized()
        try:
            user = get_authenticated_user()
            spam.dismiss_quarantined_repo(repo_uuid, user.username if user else "superuser")
            return {"status": "dismissed"}
        except spam.QuarantinedRepoNotFound:
            raise NotFound()


@resource("/v1/superuser/spam/scan")
@internal_only
@show_if(features.SUPER_USERS)
@show_if(features.SPAM_DETECTION)
class SuperUserSpamScan(ApiResource):
    @require_fresh_login
    @verify_not_prod
    @nickname("triggerSpamScan")
    @require_scope(scopes.SUPERUSER)
    def post(self):
        if not SuperUserPermission().can():
            raise Unauthorized()
        from data.model.spam_detection_engine import ScanConfig, SpamScanner

        config = ScanConfig(dry_run=True)
        scanner = SpamScanner(config)
        report = scanner.scan()
        return report.to_dict(), 200
