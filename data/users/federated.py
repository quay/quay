import logging
import features

from collections import namedtuple

from data import model
from data.users.shared import can_create_user
from util.validation import generate_valid_usernames

logger = logging.getLogger(__name__)

UserInformation = namedtuple("UserInformation", ["username", "email", "id"])

DISABLED_MESSAGE = "User creation is disabled. Please contact your administrator to gain access."


class FederatedUsers(object):
    """
    Base class for all federated users systems.
    """

    def __init__(self, federated_service, requires_email):
        self._federated_service = federated_service
        self._requires_email = requires_email

    @property
    def federated_service(self):
        return self._federated_service

    @property
    def supports_fresh_login(self):
        return True

    @property
    def supports_encrypted_credentials(self):
        return True

    def has_password_set(self, username):
        return True

    @property
    def requires_distinct_cli_password(self):
        # Since the federated auth provides a password which works on the CLI.
        return False

    def get_user(self, username_or_email):
        """
        Retrieves the user with the given username or email, returning a tuple containing a
        UserInformation (if success) and the error message (on failure).
        """
        raise NotImplementedError

    def verify_credentials(self, username_or_email, password):
        """
        Verifies the given credentials against the backing federated service, returning a tuple
        containing a UserInformation (on success) and the error message (on failure).
        """
        raise NotImplementedError

    def query_users(self, query, limit=20):
        """
        If implemented, get_user must be implemented as well.
        """
        return (None, "Not supported")

    def link_user(self, username_or_email):
        (user_info, err_msg) = self.get_user(username_or_email)
        if user_info is None:
            return (None, err_msg)

        return self.get_and_link_federated_user_info(user_info)

    def get_and_link_federated_user_info(self, user_info, internal_create=False):
        return self._get_and_link_federated_user_info(
            user_info.username, user_info.email, internal_create=internal_create
        )

    def verify_and_link_user(self, username_or_email, password):
        """
        Verifies the given credentials and, if valid, creates/links a database user to the
        associated federated service.
        """
        (credentials, err_msg) = self.verify_credentials(username_or_email, password)
        if credentials is None:
            return (None, err_msg)

        return self._get_and_link_federated_user_info(credentials.username, credentials.email)

    def confirm_existing_user(self, username, password):
        """
        Confirms that the given *database* username and service password are valid for the linked
        service.

        This method is used when the federated service's username is not known.
        """
        db_user = model.user.get_user(username)
        if not db_user:
            return (None, "Invalid user")

        federated_login = model.user.lookup_federated_login(db_user, self._federated_service)
        if not federated_login:
            return (None, "Invalid user")

        (credentials, err_msg) = self.verify_credentials(federated_login.service_ident, password)
        if credentials is None:
            return (None, err_msg)

        return (db_user, None)

    def service_metadata(self):
        """
        Returns a dictionary of extra metadata to present to *superusers* about this auth engine.

        For example, LDAP returns the base DN so we can display to the user during sync setup.
        """
        return {}

    def check_group_lookup_args(self, group_lookup_args):
        """
        Verifies that the given group lookup args point to a valid group.

        Returns a tuple consisting of a boolean status and an error message (if any).
        """
        return (False, "Not supported")

    def iterate_group_members(self, group_lookup_args, page_size=None, disable_pagination=False):
        """
        Returns an iterator over all the members of the group matching the given lookup args
        dictionary.

        The format of the lookup args dictionary is specific to the implementation.
        """
        return (None, "Not supported")

    def _get_and_link_federated_user_info(self, username, email, internal_create=False):
        db_user = model.user.verify_federated_login(self._federated_service, username)
        if not db_user:

            # Fetch list of blacklisted domains
            blacklisted_domains = model.config.app_config.get("BLACKLISTED_EMAIL_DOMAINS")

            # We must create the user in our db. Check to see if this is allowed (except for internal
            # creation, which is always allowed).
            if not internal_create and not can_create_user(email, blacklisted_domains):
                return (None, DISABLED_MESSAGE)

            valid_username = None
            for valid_username in generate_valid_usernames(username):
                if model.user.is_username_unique(valid_username):
                    break

            if not valid_username:
                logger.error("Unable to pick a username for user: %s", username)
                return (
                    None,
                    "Unable to pick a username. Please report this to your administrator.",
                )

            prompts = model.user.get_default_user_prompts(features)
            try:
                db_user = model.user.create_federated_user(
                    valid_username,
                    email,
                    self._federated_service,
                    username,
                    set_password_notification=False,
                    email_required=self._requires_email,
                    confirm_username=features.USERNAME_CONFIRMATION,
                    prompts=prompts,
                )
            except model.InvalidEmailAddressException as iae:
                return (None, str(iae))

        else:
            # Update the db attributes from the federated service.
            if email and db_user.email != email:
                db_user.email = email
                db_user.save()

        return (db_user, None)
