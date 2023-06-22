import pytest
from data import model
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
    user_1 = model.user.create_user("user1", "password", "user1@test.com")
    user_2 = model.user.create_user("user2", "password", "user2@test.com")
    user_3 = model.user.create_user("user3", "password", "user3@test.com")
    user_4 = model.user.create_user("user4", "password", "user4@test.com")
    user_5 = model.user.create_user("user5", "password", "user5@test.com")

    fourthorg = model.organization.create_organization(
        "thecollective", "tertiaryattribute@unimatrix8472.borg", user_1
    )
    fourthorg.save()

    repo1 = model.repository.create_repository(
        fourthorg.username, "repo1", fourthorg, description="First repo."
    )
    repo2 = model.repository.create_repository(
        fourthorg.username, "repo2", fourthorg, description="Second repo."
    )
    repo3 = model.repository.create_repository(
        fourthorg.username, "repo3", fourthorg, description="Third repo."
    )
    repo4 = model.repository.create_repository(
        fourthorg.username, "repo4", fourthorg, description="Fourth repo."
    )
    repo5 = model.repository.create_repository(
        fourthorg.username, "repo5", fourthorg, description="Fifth repo."
    )
    repo6 = model.repository.create_repository(
        fourthorg.username, "repo6", fourthorg, description="Sixth repo."
    )

    fourthcreators = model.team.create_team(
        "creators", fourthorg, "creator", "Creators of orgrepo."
    )
    fourthwriters = model.team.create_team("writers", fourthorg, "member", "Writers of orgrepo.")
    fourthreaders = model.team.create_team("readers", fourthorg, "member", "Readers of orgrepo.")
    fourthadmins = model.team.create_team("admins", fourthorg, "admin", "Admins of orgrepo.")
    fourthnobodies = model.team.create_team(
        "nobodies", fourthorg, "member", "No permissions actually."
    )

    collective_robot, _ = model.user.create_robot("robot1", fourthorg)

    model.team.add_user_to_team(user_2, fourthcreators)
    model.team.add_user_to_team(user_3, fourthwriters)
    model.team.add_user_to_team(user_4, fourthwriters)
    model.team.add_user_to_team(user_5, fourthreaders)
    model.team.add_user_to_team(collective_robot, fourthreaders)
    model.team.add_user_to_team(user_5, fourthadmins)
    model.team.add_user_to_team(user_5, fourthnobodies)

    model.permission.set_team_repo_permission(
        fourthwriters.name, fourthorg.username, repo1.name, "write"
    )
    model.permission.set_team_repo_permission(
        fourthwriters.name, fourthorg.username, repo2.name, "write"
    )
    model.permission.set_team_repo_permission(
        fourthreaders.name, fourthorg.username, repo3.name, "read"
    )
    model.permission.set_team_repo_permission(
        fourthreaders.name, fourthorg.username, repo4.name, "read"
    )
    model.permission.set_team_repo_permission(
        fourthadmins.name, fourthorg.username, repo5.name, "admin"
    )
    model.permission.set_team_repo_permission(
        fourthadmins.name, fourthorg.username, repo6.name, "admin"
    )

    model.permission.set_user_repo_permission(
        user_2.username, fourthorg.username, repo6.name, "write"
    )
    model.permission.set_user_repo_permission(
        collective_robot.username, fourthorg.username, repo6.name, "write"
    )

    # Get the org
    org = get_organization("thecollective")

    if not members and not collaborators:
        with pytest.raises(ValueError):
            organization_permission_report(
                org=org,
                members=members,
                collaborators=collaborators,
                include_robots=robots,
                page=1,
                page_size=100,
            )
    else:
        report, _ = organization_permission_report(
            org=org,
            members=members,
            collaborators=collaborators,
            include_robots=robots,
            page=1,
            page_size=100,
        )

        assert len(report) > 0

        if not robots:
            assert not any(
                [permission["user_name"] == collective_robot.username for permission in report]
            )
        else:
            assert any(
                [permission["user_name"] == collective_robot.username for permission in report]
            )

        if members:
            # new_user1 is in team owners (of type admins) which has no permissions yet, but it should  appear in the report because the admin role can create/delete/modify any repo
            assert any(
                [
                    permission["user_name"] == user_1.username
                    and permission["team_name"] is not None
                    and permission["team_name"] == "owners"
                    for permission in report
                ]
            )

            # new_user3 is in team writers (of type members) which has write permissions on repo2 so it should appear in the report
            assert any(
                [
                    permission["user_name"] == user_3.username
                    and permission["team_name"] is not None
                    and permission["team_name"] == "writers"
                    and permission["repository_name"] == "repo2"
                    for permission in report
                ]
            )

            # new_user2 is in team creators (of type creator) which has no permissions yet, but it should  appear in the report because the creator role can create new repos
            assert any(
                [
                    permission["user_name"] == user_2.username
                    and permission["team_name"] is not None
                    and permission["team_name"] == "creators"
                    for permission in report
                ]
            )

            # new_user5 is in team nobodies (of type member) that has no permissions yet, it should not appear in the report
            assert not any(
                [
                    permission["user_name"] == user_5.username
                    and permission["team_name"] is not None
                    and permission["team_name"] == "nobodies"
                    for permission in report
                ]
            )

        if collaborators:
            # new_user2 has directly been given write permissions on repo6 so it should appear in the report
            assert any(
                [
                    permission["user_name"] == user_2.username
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
