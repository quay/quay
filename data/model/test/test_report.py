import pytest
from data.model.report import organization_permission_report

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
            organization_permission_report(org, members, collaborators, robots)
    else:
        report = organization_permission_report(org, members, collaborators, robots)

        assert len(report) > 0

        if not robots:
            assert not any(
                [permission["username"] == "thecollective+robot1" for permission in report]
            )
        else:
            assert any(
                [permission["username"] == "thecollective+robot1" for permission in report]
            )

        if members:
            assert any(
                [
                    permission["username"] == "devtable" 
                    and permission.get("team_name") is not None
                    and permission["team_name"] == "owners"
                    for permission in report
                ]
            )
            assert any(
                [
                    permission["username"] == "freshuser"
                    and permission.get("team_name") is not None
                    and permission["team_name"] == "writers"
                    and permission["repository"] == "repo2"
                    for permission in report
                ]
            )
            assert any(
                [
                    permission["username"] == "public"
                    and permission.get("team_name") is not None
                    and permission["team_name"] == "creators"
                    for permission in report
                ]
            )

        if collaborators:
            assert any(
                [
                    permission["username"] == "public"
                    and permission["role"] == "write"
                    and permission["repository"] == "repo6"
                    for permission in report
                ]
            )

        if members and not collaborators:
            assert all([permission.get("team_name") is not None for permission in report])

        if collaborators and not members:
            assert all([permission.get("team_name") is None for permission in report])
