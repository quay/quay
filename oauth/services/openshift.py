from typing import Tuple
import logging
import urllib.parse
import json

from cachetools.func import lru_cache

from oauth.base import OAuthEndpoint, OAuthExchangeCodeException, OAuthGetUserInfoException
from oauth.login import OAuthLoginService, OAuthLoginException

logger = logging.getLogger(__name__)

OAUTH_WELLKNOWN = ".well-known/oauth-authorization-server"
DEFAULT_API_HOST = "https://openshift.default.svc/"


class DiscoveryFailureException(Exception):
    """
    Exception raised when OAuth discovery fails.
    """

    pass


class OpenshiftOAuthService(OAuthLoginService):
    """The OpenShift OAuth service implements the OAuth v2 (not OIDC) implementation for Quay.

    NOTES:
        - The OpenShift OAuth service (https://github.com/openshift/oauth-proxy) does not implement a user-info endpoint
          so the user details are returned from the Kubernetes/OpenShift users API.
        - OpenShift does not store E-mail addresses for each user, so mailing features will not be available.
    """

    def __init__(self, config, key_name, client=None):
        super(OpenshiftOAuthService, self).__init__(config, key_name)

        self._http_client = client or config.get("HTTPCLIENT")

    def login_enabled(self, config):
        return config.get("FEATURE_OPENSHIFT_LOGIN", False)

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

        The openshift-oauth service provides a reference to the User resource as validation, as seen in:
        https://github.com/openshift/oauth-proxy/blob/master/providers/openshift/provider.go#L129

        Which is used by https://github.com/openshift/oauth-proxy/blob/master/providers/openshift/provider.go#L415
        to retrieve the E-mail attribute.
        """
        return OAuthEndpoint(
            self.config.get("OPENSHIFT_API_URL", DEFAULT_API_HOST)
            + "apis/user.openshift.io/v1/users/~"
        )

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
        custom_parameters = self.config.get("OPENSHIFT_ENDPOINT_CUSTOM_PARAMS", {}).get(
            endpoint_key, {}
        )

        query_params = urllib.parse.parse_qs(query, keep_blank_values=True)
        query_params.update(kwargs)
        query_params.update(custom_parameters)
        return OAuthEndpoint(
            urllib.parse.urlunsplit((scheme, netloc, path, {}, fragment)), query_params
        )

    @lru_cache(maxsize=1)
    def _oauth_config(self):
        return self._load_oauth_config_via_discovery(self.config.get("DEBUGGING", False))

    def _load_oauth_config_via_discovery(self, is_debugging):
        """
        Attempts to load the OAuth config via the OAuth discovery mechanism using OpenShift Default Service DNS.

        If is_debugging is True, non-secure connections are alllowed. Raises an
        DiscoveryFailureException on failure.
        """
        oauth_server = self.config.get("OPENSHIFT_API_URL", DEFAULT_API_HOST)
        discovery_url = urllib.parse.urljoin(oauth_server, OAUTH_WELLKNOWN)

        # openshift.default.svc is signed by `kube-apiserver-service-network-signer` and the Quay pod may not trust
        # this OR python3 requests may not support TLS SNI?
        verify = (is_debugging is False) and (oauth_server != DEFAULT_API_HOST)
        discovery = self._http_client.get(discovery_url, timeout=5, verify=verify)
        if discovery.status_code // 100 != 2:
            logger.debug(
                "Got %s response for OpenShift OAuth discovery: %s",
                discovery.status_code,
                discovery.text,
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

    def get_login_service_id(self, user_info):
        return user_info["metadata"]["name"]

    def get_login_service_username(self, user_info):
        return user_info["metadata"]["name"]

    def get_verified_user_email(self, app_config, http_client, token, user_info):
        """OpenShift does not store E-mail as a standard attribute."""
        return None

    def get_user_info(self, http_client, token):
        """OpenShift does not provide a standard OAuth user-info endpoint, but it does provide
        API access to the Kubernetes `User` object. In this case, we map the necessary attributes
        back into something that Quay expects."""
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
        if user_info is None or "metadata" not in user_info:
            raise OAuthGetUserInfoException()

        # Unfortunately, `exchange_code_for_login` requires an `id` attribute regardless of the get_login_service_id
        # implementation.
        user_id = self.get_login_service_id(user_info)
        user_info["id"] = user_id
        return user_info
