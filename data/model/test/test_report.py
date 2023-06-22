import logging
import pytest
from data.model.report import organization_permission_report
from data.database import db

from test.fixtures import *
import pytest

from data.model.organization import get_organization


@pytest.mark.parametrize(
    "members",
    [
        (True),
        (False),
    ],
)
@pytest.mark.parametrize(
    "collaborators",
    [
        (True),
        (False),
    ],
)
@pytest.mark.parametrize(
    "robots",
    [
        (True),
        (False),
    ],
)
def test_organization_permission_report(members, collaborators, robots, initialized_db):
    # Get the org
    org = get_organization("thecollective")

    if not members and not collaborators:
        with pytest.raises(ValueError):
            organization_permission_report(
                org, members, collaborators, robots, page=1, page_size=100
            )
    else:
        report = organization_permission_report(
            org, members, collaborators, robots, page=1, page_size=100
        )

        assert len(report) > 0

        if not robots:
            assert not any(
                [permission["user_name"] == "thecollective+robot1" for permission in report]
            )
        else:
            assert any([permission["user_name"] == "thecollective+robot1" for permission in report])

        if members:
            # new_user1 is in team owners (of type admins) which has no permissions yet, but it should  appear in the report because the admin role can create/delete/modify any repo
            assert any(
                [
                    permission["user_name"] == "devtable"
                    and permission["team_name"] is not None
                    and permission["team_name"] == "owners"
                    for permission in report
                ]
            )

            # new_user3 is in team writers (of type members) which has write permissions on repo2 so it should appear in the report
            assert any(
                [
                    permission["user_name"] == "freshuser"
                    and permission["team_name"] is not None
                    and permission["team_name"] == "writers"
                    and permission["repository_name"] == "repo2"
                    for permission in report
                ]
            )

            # new_user2 is in team creators (of type creator) which has no permissions yet, but it should  appear in the report because the creator role can create new repos
            assert any(
                [
                    permission["user_name"] == "public"
                    and permission["team_name"] is not None
                    and permission["team_name"] == "creators"
                    for permission in report
                ]
            )

            # new_user5 is in team nobodies (of type member) that has no permissions yet, it should not appear in the report
            assert not any(
                [
                    permission["user_name"] == "unverified"
                    and permission["team_name"] is not None
                    and permission["team_name"] == "nobodies"
                    for permission in report
                ]
            )

        if collaborators:
            # new_user2 has directly been given write permissions on repo6 so it should appear in the report
            assert any(
                [
                    permission["user_name"] == "public"
                    and permission.get("team_name") is None
                    and permission["role"] == "write"
                    and permission["repository_name"] == "repo6"
                    for permission in report
                ]
            )

        if members and not collaborators:
            assert all([permission["team_name"] is not None for permission in report])
            assert all([permission["team_role"] is not None for permission in report])

        if collaborators and not members:
            assert all([permission["team_name"] is None for permission in report])
            assert all([permission["team_role"] is None for permission in report])
