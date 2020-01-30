import logging

from data import model
from oauth.loginmanager import OAuthLoginManager
from oauth.oidc import PublicKeyLoadException


logger = logging.getLogger(__name__)


class AppTokenInternalAuth(object):
    """
    Forces all internal credential login to go through an app token, by disabling all other access.
    """

    @property
    def supports_fresh_login(self):
        # Since there is no password.
        return False

    @property
    def federated_service(self):
        return None

    @property
    def requires_distinct_cli_password(self):
        # Since there is no supported "password".
        return False

    def has_password_set(self, username):
        # Since there is no supported "password".
        return False

    @property
    def supports_encrypted_credentials(self):
        # Since there is no supported "password".
        return False

    def verify_credentials(self, username_or_email, id_token):
        return (None, "An application specific token is required to login")

    def verify_and_link_user(self, username_or_email, password):
        return self.verify_credentials(username_or_email, password)

    def confirm_existing_user(self, username, password):
        return self.verify_credentials(username, password)

    def link_user(self, username_or_email):
        return (None, "Unsupported for this authentication system")

    def get_and_link_federated_user_info(self, user_info):
        return (None, "Unsupported for this authentication system")

    def query_users(self, query, limit):
        return (None, "", "")

    def check_group_lookup_args(self, group_lookup_args):
        return (False, "Not supported")

    def iterate_group_members(self, group_lookup_args, page_size=None, disable_pagination=False):
        return (None, "Not supported")

    def service_metadata(self):
        return {}

    def ping(self):
        """
        Always assumed to be working.

        If the DB is broken, other checks will handle it.
        """
        return (True, None)
