# -*- coding: utf-8 -*-
import tldextract

import features

from data import model


def can_create_user(email_address, blacklisted_domains=None):
    """
    Returns true if a user with the specified e-mail address can be created.
    """

    if features.BLACKLISTED_EMAILS and email_address and "@" in email_address:
        blacklisted_domains = blacklisted_domains or []
        _, email_domain = email_address.split("@", 1)
        extracted = tldextract.extract(email_domain)
        if extracted.registered_domain.lower() in blacklisted_domains:
            return False

    if not features.USER_CREATION:
        return False

    if features.INVITE_ONLY_USER_CREATION:
        if not email_address:
            return False

        # Check to see that there is an invite for the e-mail address.
        return bool(model.team.lookup_team_invites_by_email(email_address))

    # Otherwise the user can be created (assuming it doesn't already exist, of course)
    return True
