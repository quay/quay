import logging

from abc import ABCMeta, abstractmethod
from six import add_metaclass

import features

from oauth.base import OAuthService, OAuthExchangeCodeException, OAuthGetUserInfoException

logger = logging.getLogger(__name__)


class OAuthLoginException(Exception):
    """
    Exception raised if a login operation fails.
    """

    pass


@add_metaclass(ABCMeta)
class OAuthLoginService(OAuthService):
    """
    A base class for defining an OAuth-compliant service that can be used for, amongst other things,
    login and authentication.
    """

    @abstractmethod
    def login_enabled(self):
        """
        Returns true if the login service is enabled.
        """
        pass

    @abstractmethod
    def get_login_service_id(self, user_info):
        """
        Returns the internal ID for the given user under this login service.
        """
        pass

    @abstractmethod
    def get_login_service_username(self, user_info):
        """
        Returns the username for the given user under this login service.
        """
        pass

    @abstractmethod
    def get_verified_user_email(self, app_config, http_client, token, user_info):
        """
        Returns the verified email address for the given user, if any or None if none.
        """
        pass

    @abstractmethod
    def get_icon(self):
        """
        Returns the icon to display for this login service.
        """
        pass

    @abstractmethod
    def get_login_scopes(self):
        """
        Returns the list of scopes for login for this service.
        """
        pass

    def service_verify_user_info_for_login(self, app_config, http_client, token, user_info):
        """
        Performs service-specific verification of user information for login.

        On failure, a service should raise a OAuthLoginService.
        """
        # By default, does nothing.
        pass

    def exchange_code_for_login(self, app_config, http_client, code, redirect_suffix):
        """
        Exchanges the given OAuth access code for user information on behalf of a user trying to
        login or attach their account.

        Raises a OAuthLoginService exception on failure. Returns a tuple consisting of (service_id,
        service_username, email)
        """

        # Retrieve the token for the OAuth code.
        try:
            token = self.exchange_code_for_token(
                app_config,
                http_client,
                code,
                redirect_suffix=redirect_suffix,
                form_encode=self.requires_form_encoding(),
            )
        except OAuthExchangeCodeException as oce:
            raise OAuthLoginException(str(oce))

        # Retrieve the user's information with the token.
        try:
            user_info = self.get_user_info(http_client, token)
        except OAuthGetUserInfoException as oge:
            raise OAuthLoginException(str(oge))

        if user_info.get("id", None) is None:
            logger.debug("Got user info response %s", user_info)
            raise OAuthLoginException("Missing `id` column in returned user information")

        # Perform any custom verification for this login service.
        self.service_verify_user_info_for_login(app_config, http_client, token, user_info)

        # Retrieve the user's email address (if necessary).
        email_address = self.get_verified_user_email(app_config, http_client, token, user_info)
        if features.MAILING and email_address is None:
            raise OAuthLoginException(
                "A verified email address is required to login with this service"
            )

        service_user_id = self.get_login_service_id(user_info)
        service_username = self.get_login_service_username(user_info)

        logger.debug(
            "Completed successful exchange for service %s: %s, %s, %s",
            self.service_id(),
            service_user_id,
            service_username,
            email_address,
        )
        return (service_user_id, service_username, email_address)
