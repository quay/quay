import copy
import logging
import requests
import time
import urllib.request, urllib.parse, urllib.error
import urllib.parse

from abc import ABCMeta, abstractmethod
from six import add_metaclass
from six.moves.urllib.parse import quote

from util.config import URLSchemeAndHostname

logger = logging.getLogger(__name__)


class OAuthEndpoint(object):
    def __init__(self, base_url, params=None):
        self.base_url = base_url
        self.params = params or {}

    def with_param(self, name, value):
        params_copy = copy.copy(self.params)
        params_copy[name] = value
        return OAuthEndpoint(self.base_url, params_copy)

    def with_params(self, parameters):
        params_copy = copy.copy(self.params)
        params_copy.update(parameters)
        return OAuthEndpoint(self.base_url, params_copy)

    def to_url(self):
        (scheme, netloc, path, _, fragment) = urllib.parse.urlsplit(self.base_url)
        updated_query = urllib.parse.urlencode(self.params)
        return urllib.parse.urlunsplit((scheme, netloc, path, updated_query, fragment))


class OAuthExchangeCodeException(Exception):
    """
    Exception raised if a code exchange fails.
    """

    pass


class OAuthGetUserInfoException(Exception):
    """
    Exception raised if a call to get user information fails.
    """

    pass


@add_metaclass(ABCMeta)
class OAuthService(object):
    """
    A base class for defining an external service, exposed via OAuth.
    """

    def __init__(self, config, key_name):
        self.key_name = key_name
        self.config = config.get(key_name) or {}
        self._is_testing = config.get("TESTING")

    @abstractmethod
    def service_id(self):
        """
        The internal ID for this service.

        Must match the URL portion for the service, e.g. `github`
        """
        pass

    @abstractmethod
    def service_name(self):
        """
        The user-readable name for the service, e.g. `GitHub`
        """
        pass

    @abstractmethod
    def token_endpoint(self):
        """
        Returns the endpoint at which the OAuth code can be exchanged for a token.
        """
        pass

    @abstractmethod
    def user_endpoint(self):
        """
        Returns the endpoint at which user information can be looked up.
        """
        pass

    @abstractmethod
    def authorize_endpoint(self):
        """
        Returns the for authorization of the OAuth service.
        """
        pass

    @abstractmethod
    def validate_client_id_and_secret(self, http_client, url_scheme_and_hostname):
        """
        Performs validation of the client ID and secret, raising an exception on failure.
        """
        pass

    def requires_form_encoding(self):
        """
        Returns True if form encoding is necessary for the exchange_code_for_token call.
        """
        return False

    def client_id(self):
        return self.config.get("CLIENT_ID")

    def client_secret(self):
        return self.config.get("CLIENT_SECRET")

    def login_binding_field(self):
        """
        Returns the name of the field (`username` or `email`) used for auto binding an external
        login service account to an *internal* login service account.

        For example, if the external login service is GitHub and the internal login service is LDAP,
        a value of `email` here will cause login-with-Github to conduct a search (via email) in LDAP
        for a user, an auto bind the external and internal users together. May return None, in which
        case no binding is performing, and login with this external account will simply create a new
        account in the database.
        """
        return self.config.get("LOGIN_BINDING_FIELD", None)

    def get_auth_url(self, url_scheme_and_hostname, redirect_suffix, csrf_token, scopes):
        """
        Retrieves the authorization URL for this login service.
        """
        redirect_uri = "%s/oauth2/%s/callback%s" % (
            url_scheme_and_hostname.get_url(),
            self.service_id(),
            redirect_suffix,
        )
        params = {
            "client_id": self.client_id(),
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": quote(csrf_token),
        }

        return self.authorize_endpoint().with_params(params).to_url()

    def get_redirect_uri(self, url_scheme_and_hostname, redirect_suffix=""):
        return "%s://%s/oauth2/%s/callback%s" % (
            url_scheme_and_hostname.url_scheme,
            url_scheme_and_hostname.hostname,
            self.service_id(),
            redirect_suffix,
        )

    def get_user_info(self, http_client, token):
        token_param = {
            "alt": "json",
        }

        headers = {
            "Authorization": "Bearer %s" % token,
        }

        got_user = http_client.get(
            self.user_endpoint().to_url(), params=token_param, headers=headers
        )
        if got_user.status_code // 100 != 2:
            raise OAuthGetUserInfoException(
                "Non-2XX response code for user_info call: %s" % got_user.status_code
            )

        user_info = got_user.json()
        if user_info is None:
            raise OAuthGetUserInfoException()

        return user_info

    def exchange_code_for_token(
        self,
        app_config,
        http_client,
        code,
        form_encode=False,
        redirect_suffix="",
        client_auth=False,
    ):
        """
        Exchanges an OAuth access code for the associated OAuth token.
        """
        json_data = self.exchange_code(
            app_config, http_client, code, form_encode, redirect_suffix, client_auth
        )

        access_token = json_data.get("access_token", None)
        if access_token is None:
            logger.debug(
                "Got successful get_access_token response with missing token: %s", json_data
            )
            raise OAuthExchangeCodeException("Missing `access_token` in OAuth response")

        return access_token

    def exchange_code(
        self,
        app_config,
        http_client,
        code,
        form_encode=False,
        redirect_suffix="",
        client_auth=False,
    ):
        """
        Exchanges an OAuth access code for associated OAuth token and other data.
        """
        url_scheme_and_hostname = URLSchemeAndHostname.from_app_config(app_config)
        payload = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.get_redirect_uri(url_scheme_and_hostname, redirect_suffix),
        }
        headers = {"Accept": "application/json"}

        auth = None
        if client_auth:
            auth = (self.client_id(), self.client_secret())
        else:
            payload["client_id"] = self.client_id()
            payload["client_secret"] = self.client_secret()

        token_url = self.token_endpoint().to_url()

        def perform_request():
            attempts = 0
            max_attempts = 3
            timeout = 5 / 1000

            while attempts < max_attempts:
                if self._is_testing:
                    headers["X-Quay-Retry-Attempts"] = str(attempts)

                try:
                    if form_encode:
                        return http_client.post(
                            token_url, data=payload, headers=headers, auth=auth, timeout=5
                        )
                    else:
                        return http_client.post(
                            token_url, params=payload, headers=headers, auth=auth, timeout=5
                        )
                except requests.ConnectionError:
                    logger.debug("Got ConnectionError during OAuth token exchange, retrying.")
                    attempts += 1
                    time.sleep(timeout)

        get_access_token = perform_request()
        if get_access_token is None:
            logger.debug("Received too many ConnectionErrors during code exchange")
            raise OAuthExchangeCodeException(
                "Received too many ConnectionErrors during code exchange"
            )

        if get_access_token.status_code // 100 != 2:
            logger.debug("Got get_access_token response %s", get_access_token.text)
            raise OAuthExchangeCodeException(
                "Got non-2XX response for code exchange: %s" % get_access_token.status_code
            )

        json_data = get_access_token.json()
        if not json_data:
            raise OAuthExchangeCodeException("Got non-JSON response for code exchange")

        if "error" in json_data:
            raise OAuthExchangeCodeException(json_data.get("error_description", json_data["error"]))

        return json_data
