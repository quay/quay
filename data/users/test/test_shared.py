import pytest

from mock import patch

from data import model
from data.users.shared import can_create_user

from test.fixtures import *


@pytest.mark.parametrize(
    "open_creation, invite_only, email, has_invite, can_create",
    [
        # Open user creation => always allowed.
        (True, False, None, False, True),
        # Open user creation => always allowed.
        (True, False, "foo@example.com", False, True),
        # Invite only user creation + no invite => disallowed.
        (True, True, None, False, False),
        # Invite only user creation + no invite => disallowed.
        (True, True, "foo@example.com", False, False),
        # Invite only user creation + invite => allowed.
        (True, True, "foo@example.com", True, True),
        # No open creation => Disallowed.
        (False, True, "foo@example.com", False, False),
        (False, True, "foo@example.com", True, False),
        # Blacklisted emails => Disallowed.
        (True, False, "foo@blacklisted.com", False, False),
        (True, False, "foo@blacklisted.org", False, False),
        (True, False, "foo@BlAcKlIsTeD.CoM", False, False),  # Verify Capitalization
        (True, False, "foo@mail.bLacklisted.Com", False, False),  # Verify unicode
        (True, False, "foo@blacklisted.net", False, True),  # Avoid False Positives
        (True, False, "foo@myblacklisted.com", False, True),  # Avoid partial domain matches
        (True, False, "fooATblacklisted.com", False, True),  # Ignore invalid email addresses
    ],
)
@pytest.mark.parametrize("blacklisting_enabled", [True, False])
def test_can_create_user(
    open_creation, invite_only, email, has_invite, can_create, blacklisting_enabled, app
):

    # Mock list of blacklisted domains
    blacklisted_domains = ["blacklisted.com", "blacklisted.org"]

    if has_invite:
        inviter = model.user.get_user("devtable")
        team = model.team.get_organization_team("buynlarge", "owners")
        model.team.add_or_invite_to_team(inviter, team, email=email)

    with patch("features.USER_CREATION", open_creation):
        with patch("features.INVITE_ONLY_USER_CREATION", invite_only):
            with patch("features.BLACKLISTED_EMAILS", blacklisting_enabled):
                if (
                    email
                    and any(domain in email.lower() for domain in blacklisted_domains)
                    and not blacklisting_enabled
                ):
                    can_create = (
                        True  # blacklisted domains can be used, if blacklisting is disabled
                    )
                assert can_create_user(email, blacklisted_domains) == can_create
