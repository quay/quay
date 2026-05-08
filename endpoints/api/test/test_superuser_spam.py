import pytest

import features
from endpoints.api.superuser_spam import (
    SuperUserDismissRepo,
    SuperUserFlaggedRepoDetail,
    SuperUserFlaggedRepoList,
    SuperUserQuarantineRepo,
    SuperUserRestoreRepo,
    SuperUserSpamRuleDetail,
    SuperUserSpamRuleList,
    SuperUserSpamScan,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *

SPAM_FEATURES = {
    "FEATURE_SPAM_DETECTION": True,
    "FEATURE_SUPER_USERS": True,
    "FEATURE_SUPERUSERS_FULL_ACCESS": True,
}

VALID_RULE_BODY = {
    "name": "test-keyword-rule",
    "rule_type": "keyword",
    "pattern": "spam,buy,cheap",
    "confidence_score": 75,
}


def _enable_features():
    features.import_features(SPAM_FEATURES)


def _create_rule(cl):
    return conduct_api_call(cl, SuperUserSpamRuleList, "POST", None, VALID_RULE_BODY, 201).json


def test_list_spam_rules(app):
    _enable_features()
    with client_with_identity("devtable", app) as cl:
        result = conduct_api_call(cl, SuperUserSpamRuleList, "GET", None, None, 200).json
        assert "rules" in result
        assert isinstance(result["rules"], list)


def test_create_spam_rule(app):
    _enable_features()
    with client_with_identity("devtable", app) as cl:
        result = _create_rule(cl)
        assert result["name"] == VALID_RULE_BODY["name"]
        assert result["rule_type"] == VALID_RULE_BODY["rule_type"]
        assert result["pattern"] == VALID_RULE_BODY["pattern"]
        assert result["confidence_score"] == VALID_RULE_BODY["confidence_score"]
        assert "uuid" in result


def test_create_spam_rule_invalid_type(app):
    _enable_features()
    with client_with_identity("devtable", app) as cl:
        body = {
            "name": "bad-rule",
            "rule_type": "nonexistent_type",
        }
        conduct_api_call(cl, SuperUserSpamRuleList, "POST", None, body, 400)


def test_get_spam_rule_by_uuid(app):
    _enable_features()
    with client_with_identity("devtable", app) as cl:
        created = _create_rule(cl)
        rule_uuid = created["uuid"]
        result = conduct_api_call(
            cl, SuperUserSpamRuleDetail, "GET", {"rule_uuid": rule_uuid}, None, 200
        ).json
        assert result["uuid"] == rule_uuid
        assert result["name"] == VALID_RULE_BODY["name"]


def test_get_spam_rule_not_found(app):
    _enable_features()
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl, SuperUserSpamRuleDetail, "GET", {"rule_uuid": "nonexistent-uuid"}, None, 404
        )


def test_update_spam_rule(app):
    _enable_features()
    with client_with_identity("devtable", app) as cl:
        created = _create_rule(cl)
        rule_uuid = created["uuid"]
        update_body = {"name": "updated-rule-name", "confidence_score": 90}
        result = conduct_api_call(
            cl, SuperUserSpamRuleDetail, "PUT", {"rule_uuid": rule_uuid}, update_body, 200
        ).json
        assert result["name"] == "updated-rule-name"
        assert result["confidence_score"] == 90


def test_update_spam_rule_not_found(app):
    _enable_features()
    with client_with_identity("devtable", app) as cl:
        update_body = {"name": "does-not-matter"}
        conduct_api_call(
            cl, SuperUserSpamRuleDetail, "PUT", {"rule_uuid": "nonexistent-uuid"}, update_body, 404
        )


def test_delete_spam_rule(app):
    _enable_features()
    with client_with_identity("devtable", app) as cl:
        created = _create_rule(cl)
        rule_uuid = created["uuid"]
        conduct_api_call(cl, SuperUserSpamRuleDetail, "DELETE", {"rule_uuid": rule_uuid}, None, 204)
        conduct_api_call(cl, SuperUserSpamRuleDetail, "GET", {"rule_uuid": rule_uuid}, None, 404)


def test_delete_spam_rule_not_found(app):
    _enable_features()
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl, SuperUserSpamRuleDetail, "DELETE", {"rule_uuid": "nonexistent-uuid"}, None, 404
        )


def test_list_flagged_repos(app):
    _enable_features()
    with client_with_identity("devtable", app) as cl:
        result = conduct_api_call(cl, SuperUserFlaggedRepoList, "GET", None, None, 200).json
        assert "flagged_repos" in result
        assert isinstance(result["flagged_repos"], list)


def test_get_flagged_repo_not_found(app):
    _enable_features()
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl, SuperUserFlaggedRepoDetail, "GET", {"repo_uuid": "nonexistent-uuid"}, None, 404
        )


def test_quarantine_repo_not_found(app):
    _enable_features()
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl, SuperUserQuarantineRepo, "POST", {"repo_uuid": "nonexistent-uuid"}, None, 404
        )


def test_restore_repo_not_found(app):
    _enable_features()
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl, SuperUserRestoreRepo, "POST", {"repo_uuid": "nonexistent-uuid"}, None, 404
        )


def test_dismiss_repo_not_found(app):
    _enable_features()
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl, SuperUserDismissRepo, "POST", {"repo_uuid": "nonexistent-uuid"}, None, 404
        )


def test_trigger_spam_scan(app):
    _enable_features()
    with client_with_identity("devtable", app) as cl:
        result = conduct_api_call(cl, SuperUserSpamScan, "POST", None, None, 200).json
        assert "scan_id" in result
        assert "total_scanned" in result
        assert "flagged" in result
        assert "clean" in result
        assert "errors" in result
