import logging
import urllib.parse
import json

from cachetools.func import lru_cache

import features
from oauth.base import OAuthEndpoint, OAuthExchangeCodeException, OAuthGetUserInfoException
from oauth.login import OAuthLoginService, OAuthLoginException
from util import slash_join

logger = logging.getLogger(__name__)

OAUTH_WELLKNOWN = ".well-known/oauth-authorization-server"
DEFAULT_OAUTH_HOST = "https://openshift.default.svc/"


class DiscoveryFailureException(Exception):
    """
    Exception raised when OAuth discovery fails.
    """

    pass


class OpenshiftOAuthService(OAuthLoginService):

    def __init__(self, config, key_name, client=None):
        super(OpenshiftOAuthService, self).__init__(config, key_name)

        self._http_client = client or config.get("HTTPCLIENT")

    def login_enabled(self, config):
        return config.get("FEATURE_OPENSHIFT_LOGIN", False)

    def get_login_service_id(self, user_info):
        return user_info['metadata']['name']

    def get_login_service_username(self, user_info):
        return user_info['metadata']['name']

    def get_verified_user_email(self, app_config, http_client, token, user_info):
        pass

    def get_icon(self):
        return "fa-redhat"

    def get_login_scopes(self):
        return ["user:info", "user:list-projects"]

    def service_id(self):
        return "openshift"

    def service_name(self):
        return "OpenShift"

    def authorize_endpoint(self):
        return self._get_endpoint("authorization_endpoint").with_param("response_type", "code")

    def token_endpoint(self):
        return self._get_endpoint("token_endpoint")

    def user_endpoint(self):
        """Technically the user endpoint is the Kubernetes API itself in the OpenShift situation.
        Reference implementation: https://github.com/openshift/oauth-proxy/blob/master/providers/openshift/provider.go
        """
        return OAuthEndpoint(self.config.get("OPENSHIFT_SERVER") + "apis/user.openshift.io/v1/users/~")

    def validate_client_id_and_secret(self, http_client, url_scheme_and_hostname):
        """TODO: provide means of validation with internal OAuth service."""
        return True

    def _get_endpoint(self, endpoint_key, **kwargs):
        """
        Returns the OIDC endpoint with the given key found in the OIDC discovery document, with the
        given kwargs added as query parameters.

        Additionally, any defined parameters found in the OIDC configuration block are also added.
        """
        endpoint = self._oauth_config().get(endpoint_key, "")
        if not endpoint:
            return None

        (scheme, netloc, path, query, fragment) = urllib.parse.urlsplit(endpoint)

        # Add the query parameters from the kwargs and the config.
        custom_parameters = self.config.get("OPENSHIFT_ENDPOINT_CUSTOM_PARAMS", {}).get(endpoint_key, {})

        query_params = urllib.parse.parse_qs(query, keep_blank_values=True)
        query_params.update(kwargs)
        query_params.update(custom_parameters)
        return OAuthEndpoint(
            urllib.parse.urlunsplit((scheme, netloc, path, {}, fragment)), query_params
        )

    @lru_cache(maxsize=1)
    def _oauth_config(self):
        if self.config.get("OPENSHIFT_SERVER"):
            return self._load_oauth_config_via_discovery(self.config.get("DEBUGGING", False))
        else:
            return {}

    def _load_oauth_config_via_discovery(self, is_debugging):
        """
        Attempts to load the OAuth config via the OAuth discovery mechanism using OpenShift Default Service DNS.

        If is_debugging is True, non-secure connections are alllowed. Raises an
        DiscoveryFailureException on failure.
        """
        oauth_server = self.config.get("OPENSHIFT_SERVER", DEFAULT_OAUTH_HOST)
        # if not oidc_server.startswith("https://") and not is_debugging:
        #     raise DiscoveryFailureException("OIDC server must be accessed over SSL")

        discovery_url = urllib.parse.urljoin(oauth_server, OAUTH_WELLKNOWN)
        discovery = self._http_client.get(discovery_url, timeout=5, verify=is_debugging is False)
        if discovery.status_code // 100 != 2:
            logger.debug(
                "Got %s response for OpenShift OAuth discovery: %s", discovery.status_code, discovery.text
            )
            raise DiscoveryFailureException("Could not load OpenShift OAuth discovery information")

        try:
            return json.loads(discovery.text)
        except ValueError:
            logger.exception("Could not parse OpenShift OAuth discovery for url: %s", discovery_url)
            raise DiscoveryFailureException("Could not parse OpenShift OAuth discovery information")

    def get_public_config(self):
        return {
            "CLIENT_ID": self.client_id(),
            "OAUTH": True,
        }

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

        # if user_info.get("id", None) is None:
        #     logger.debug("Got user info response %s", user_info)
        #     raise OAuthLoginException("Missing `id` column in returned user information")

        # Perform any custom verification for this login service.
        # self.service_verify_user_info_for_login(app_config, http_client, token, user_info)

        # Retrieve the user's email address (if necessary).
        # email_address = self.get_verified_user_email(app_config, http_client, token, user_info)
        # if features.MAILING and email_address is None:
        #     raise OAuthLoginException(
        #         "A verified email address is required to login with this service"
        #     )
        #
        email_address = None
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
