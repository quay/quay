import pytest

from auth.workload_identity import (
    WorkloadIdentityAuthorizationError,
    authorize_workload_identity_scope,
)

ISSUER = "https://kubernetes.default.svc"
SUBJECT = "system:serviceaccount:quay:controller"
MAPPING = [{"ISSUER": ISSUER, "SUBJECT": SUBJECT, "SCOPES": "repo:write repo:read"}]


@pytest.mark.parametrize(
    "issuer, subject, requested, expected",
    [
        (ISSUER, SUBJECT, "repo:read", "repo:read"),
        (ISSUER + "/", SUBJECT, "repo:read repo:read", "repo:read"),
        (ISSUER, SUBJECT, "", "repo:read repo:write"),
        (ISSUER, SUBJECT, "repo:write repo:read", "repo:read repo:write"),
    ],
)
def test_authorize_workload_identity_scope(issuer, subject, requested, expected):
    assert authorize_workload_identity_scope(MAPPING, issuer, subject, requested) == expected


@pytest.mark.parametrize(
    "issuer, subject, requested, mappings",
    [
        ("https://other", SUBJECT, "repo:read", MAPPING),
        (ISSUER, SUBJECT + "-evil", "repo:read", MAPPING),
        (ISSUER, SUBJECT, "repo:admin", MAPPING),
        (ISSUER, SUBJECT, "   ", [{"ISSUER": ISSUER, "SUBJECT": SUBJECT, "SCOPES": ""}]),
        (ISSUER, SUBJECT, "repo:read\tbad", MAPPING),
        (ISSUER, SUBJECT, 'repo:read"bad', MAPPING),
        (ISSUER, SUBJECT, "repo:read\\bad", MAPPING),
        (
            ISSUER,
            SUBJECT,
            "repo:read",
            [{"ISSUER": ISSUER, "SUBJECT": SUBJECT, "SCOPES": "repo:read\tbad"}],
        ),
    ],
)
def test_authorization_rejects_invalid_mapping(issuer, subject, requested, mappings):
    with pytest.raises(WorkloadIdentityAuthorizationError):
        authorize_workload_identity_scope(mappings, issuer, subject, requested)
