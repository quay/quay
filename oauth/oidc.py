import time
import json
import logging
import urllib.parse

import jwt

from cachetools.func import lru_cache
from cachetools.ttl import TTLCache
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_der_public_key
from jwkest.jwk import KEYS

from oauth.base import (
    OAuthService,
    OAuthExchangeCodeException,
    OAuthGetUserInfoException,
    OAuthEndpoint,
)
from oauth.login import OAuthLoginException
from util.security.jwtutil import decode, InvalidTokenError

logger = logging.getLogger(__name__)


OIDC_WELLKNOWN = ".well-known/openid-configuration"
PUBLIC_KEY_CACHE_TTL = 3600  # 1 hour
ALLOWED_ALGORITHMS = ["RS256"]
JWT_CLOCK_SKEW_SECONDS = 30


class DiscoveryFailureException(Exception):
    """
    Exception raised when OIDC discovery fails.
    """

    pass


class PublicKeyLoadException(Exception):
    """
    Exception raised if loading the OIDC public key fails.
    """

    pass


class OIDCLoginService(OAuthService):
    """
    Defines a generic service for all OpenID-connect compatible login services.
    """

    def __init__(self, config, key_name, client=None):
        super(OIDCLoginService, self).__init__(config, key_name)

        self._id = key_name[0 : key_name.find("_")].lower()
        self._http_client = client or config.get("HTTPCLIENT")
        self._mailing = config.get("FEATURE_MAILING", False)
        self._public_key_cache = _PublicKeyCache(self, 1, PUBLIC_KEY_CACHE_TTL)

    def service_id(self):
        return self._id

    def service_name(self):
        return self.config.get("SERVICE_NAME", self.service_id())

    def get_icon(self):
        return self.config.get("SERVICE_ICON", "fa-user-circle")

    def get_login_scopes(self):
        default_scopes = ["openid"]

        if self.user_endpoint() is not None:
            default_scopes.append("profile")

        if self._mailing:
            default_scopes.append("email")

        supported_scopes = self._oidc_config().get("scopes_supported", default_scopes)
        login_scopes = self.config.get("LOGIN_SCOPES") or supported_scopes
        return list(set(login_scopes) & set(supported_scopes))

    def authorize_endpoint(self):
        return self._get_endpoint("authorization_endpoint").with_param("response_type", "code")

    def token_endpoint(self):
        return self._get_endpoint("token_endpoint")

    def user_endpoint(self):
        return self._get_endpoint("userinfo_endpoint")

    def _get_endpoint(self, endpoint_key, **kwargs):
        """
        Returns the OIDC endpoint with the given key found in the OIDC discovery document, with the
        given kwargs added as query parameters.

        Additionally, any defined parameters found in the OIDC configuration block are also added.
        """
        endpoint = self._oidc_config().get(endpoint_key, "")
        if not endpoint:
            return None

        (scheme, netloc, path, query, fragment) = urllib.parse.urlsplit(endpoint)

        # Add the query parameters from the kwargs and the config.
        custom_parameters = self.config.get("OIDC_ENDPOINT_CUSTOM_PARAMS", {}).get(endpoint_key, {})

        query_params = urllib.parse.parse_qs(query, keep_blank_values=True)
        query_params.update(kwargs)
        query_params.update(custom_parameters)
        return OAuthEndpoint(
            urllib.parse.urlunsplit((scheme, netloc, path, {}, fragment)), query_params
        )

    def validate(self):
        return bool(self.get_login_scopes())

    def validate_client_id_and_secret(self, http_client, url_scheme_and_hostname):
        # TODO: find a way to verify client secret too.
        check_auth_url = http_client.get(self.get_auth_url(url_scheme_and_hostname, "", "", []))
        if check_auth_url.status_code // 100 != 2:
            raise Exception("Got non-200 status code for authorization endpoint")

    def requires_form_encoding(self):
        return True

    def get_public_config(self):
        return {
            "CLIENT_ID": self.client_id(),
            "OIDC": True,
        }

    def exchange_code_for_tokens(self, app_config, http_client, code, redirect_suffix):
        # Exchange the code for the access token and id_token
        try:
            json_data = self.exchange_code(
                app_config,
                http_client,
                code,
                redirect_suffix=redirect_suffix,
                form_encode=self.requires_form_encoding(),
            )
        except OAuthExchangeCodeException as oce:
            raise OAuthLoginException(str(oce))

        # Make sure we received both.
        access_token = json_data.get("access_token", None)
        if access_token is None:
            logger.debug("Missing access_token in response: %s", json_data)
            raise OAuthLoginException("Missing `access_token` in OIDC response")

        id_token = json_data.get("id_token", None)
        if id_token is None:
            logger.debug("Missing id_token in response: %s", json_data)
            raise OAuthLoginException("Missing `id_token` in OIDC response")

        return id_token, access_token

    def exchange_code_for_login(self, app_config, http_client, code, redirect_suffix):
        # Exchange the code for the access token and id_token
        id_token, access_token = self.exchange_code_for_tokens(
            app_config, http_client, code, redirect_suffix
        )

        # Decode the id_token.
        try:
            decoded_id_token = self.decode_user_jwt(id_token)
        except InvalidTokenError as ite:
            logger.exception("Got invalid token error on OIDC decode: %s", ite)
            raise OAuthLoginException("Could not decode OIDC token")
        except PublicKeyLoadException as pke:
            logger.exception("Could not load public key during OIDC decode: %s", pke)
            raise OAuthLoginException("Could find public OIDC key")

        # If there is a user endpoint, use it to retrieve the user's information. Otherwise, we use
        # the decoded ID token.
        if self.user_endpoint():
            # Retrieve the user information.
            try:
                user_info = self.get_user_info(http_client, access_token)
            except OAuthGetUserInfoException as oge:
                raise OAuthLoginException(str(oge))
        else:
            user_info = decoded_id_token

        # Verify subs.
        if user_info["sub"] != decoded_id_token["sub"]:
            logger.debug(
                "Mismatch in `sub` returned by OIDC user info endpoint: %s vs %s",
                user_info["sub"],
                decoded_id_token["sub"],
            )
            raise OAuthLoginException("Mismatch in `sub` returned by OIDC user info endpoint")

        # Check if we have a verified email address.
        if self.config.get("VERIFIED_EMAIL_CLAIM_NAME"):
            email_address = user_info.get(self.config["VERIFIED_EMAIL_CLAIM_NAME"])
        else:
            email_address = user_info.get("email") if user_info.get("email_verified") else None

        logger.debug("Found e-mail address `%s` for sub `%s`", email_address, user_info["sub"])
        if self._mailing:
            if email_address is None:
                raise OAuthLoginException(
                    "A verified email address is required to login with this service"
                )

        # Check for a preferred username.
        if self.config.get("PREFERRED_USERNAME_CLAIM_NAME"):
            lusername = user_info.get(self.config["PREFERRED_USERNAME_CLAIM_NAME"])
        else:
            lusername = user_info.get("preferred_username")
            if lusername is None:
                # Note: Active Directory provides `unique_name` and `upn`.
                # https://docs.microsoft.com/en-us/azure/active-directory/develop/v1-id-and-access-tokens
                lusername = user_info.get("unique_name", user_info.get("upn"))

        if lusername is None:
            lusername = user_info["sub"]

        if lusername.find("@") >= 0:
            lusername = lusername[0 : lusername.find("@")]

        return decoded_id_token["sub"], lusername, email_address

    @property
    def _issuer(self):
        # Read the issuer from the OIDC config, falling back to the configured OIDC server.
        issuer = self._oidc_config().get("issuer", self.config["OIDC_SERVER"])

        # If specified, use the overridden OIDC issuer.
        return self.config.get("OIDC_ISSUER", issuer)

    @lru_cache(maxsize=1)
    def _oidc_config(self):
        if self.config.get("OIDC_SERVER"):
            return self._load_oidc_config_via_discovery(self.config.get("DEBUGGING", False))
        else:
            return {}

    def _load_oidc_config_via_discovery(self, is_debugging):
        """
        Attempts to load the OIDC config via the OIDC discovery mechanism.

        If is_debugging is True, non-secure connections are alllowed. Raises an
        DiscoveryFailureException on failure.
        """
        oidc_server = self.config["OIDC_SERVER"]
        if not oidc_server.startswith("https://") and not is_debugging:
            raise DiscoveryFailureException("OIDC server must be accessed over SSL")

        discovery_url = urllib.parse.urljoin(oidc_server, OIDC_WELLKNOWN)
        discovery = self._http_client.get(discovery_url, timeout=5, verify=is_debugging is False)
        if discovery.status_code // 100 != 2:
            logger.debug(
                "Got %s response for OIDC discovery: %s", discovery.status_code, discovery.text
            )
            raise DiscoveryFailureException("Could not load OIDC discovery information")

        try:
            return json.loads(discovery.text)
        except ValueError:
            logger.exception("Could not parse OIDC discovery for url: %s", discovery_url)
            raise DiscoveryFailureException("Could not parse OIDC discovery information")

    def decode_user_jwt(self, token):
        """
        Decodes the given JWT under the given provider and returns it.

        Raises an InvalidTokenError exception on an invalid token or a PublicKeyLoadException if the
        public key could not be loaded for decoding.
        """
        # Find the key to use.
        headers = jwt.get_unverified_header(token)
        kid = headers.get("kid", None)
        if kid is None:
            raise InvalidTokenError("Missing `kid` header")

        logger.debug(
            "Using key `%s`, attempting to decode token `%s` with aud `%s` and iss `%s`",
            kid,
            token,
            self.client_id(),
            self._issuer,
        )
        try:
            return decode(
                token,
                self._get_public_key(kid),
                algorithms=ALLOWED_ALGORITHMS,
                audience=self.client_id(),
                issuer=self._issuer,
                leeway=JWT_CLOCK_SKEW_SECONDS,
                options=dict(require_nbf=False),
            )
        except InvalidTokenError as ite:
            logger.warning(
                "Could not decode token `%s` for OIDC: %s. Will attempt again after "
                + "retrieving public keys.",
                token,
                ite,
            )

            # Public key may have expired. Try to retrieve an updated public key and use it to decode.
            try:
                return decode(
                    token,
                    self._get_public_key(kid, force_refresh=True),
                    algorithms=ALLOWED_ALGORITHMS,
                    audience=self.client_id(),
                    issuer=self._issuer,
                    leeway=JWT_CLOCK_SKEW_SECONDS,
                    options=dict(require_nbf=False),
                )
            except InvalidTokenError as ite:
                logger.warning(
                    "Could not decode token `%s` for OIDC: %s. Attempted again after "
                    + "retrieving public keys.",
                    token,
                    ite,
                )

                # Decode again with verify=False, and log the decoded token to allow for easier debugging.
                nonverified = decode(
                    token,
                    self._get_public_key(kid, force_refresh=True),
                    algorithms=ALLOWED_ALGORITHMS,
                    audience=self.client_id(),
                    issuer=self._issuer,
                    leeway=JWT_CLOCK_SKEW_SECONDS,
                    options=dict(require_nbf=False, verify=False),
                )
                logger.debug("Got an error when trying to verify OIDC JWT: %s", nonverified)
                raise ite

    def _get_public_key(self, kid, force_refresh=False):
        """
        Retrieves the public key for this handler with the given kid.

        Raises a PublicKeyLoadException on failure.
        """

        # If force_refresh is true, we expire all the items in the cache by setting the time to
        # the current time + the expiration TTL.
        if force_refresh:
            self._public_key_cache.expire(time=time.time() + PUBLIC_KEY_CACHE_TTL)

        # Retrieve the public key from the cache. If the cache does not contain the public key,
        # it will internally call _load_public_key to retrieve it and then save it.
        return self._public_key_cache[kid]


class _PublicKeyCache(TTLCache):
    def __init__(self, login_service, *args, **kwargs):
        super(_PublicKeyCache, self).__init__(*args, **kwargs)

        self._login_service = login_service

    def __missing__(self, kid):
        """
        Loads the public key for this handler from the OIDC service.

        Raises PublicKeyLoadException on failure.
        """
        keys_url = self._login_service._oidc_config()["jwks_uri"]

        # Load the keys.
        try:
            keys = KEYS()
            keys.load_from_url(
                keys_url, verify=not self._login_service.config.get("DEBUGGING", False)
            )
        except Exception as ex:
            logger.exception("Exception loading public key")
            raise PublicKeyLoadException(str(ex))

        # Find the matching key.
        keys_found = keys.by_kid(kid)
        if len(keys_found) == 0:
            raise PublicKeyLoadException("Public key %s not found" % kid)

        rsa_keys = [key for key in keys_found if key.kty == "RSA"]
        if len(rsa_keys) == 0:
            raise PublicKeyLoadException("No RSA form of public key %s not found" % kid)

        matching_key = rsa_keys[0]
        matching_key.deserialize()

        # Reload the key so that we can give a key *instance* to PyJWT to work around its weird parsing
        # issues.
        final_key = load_der_public_key(
            matching_key.key.exportKey("DER"), backend=default_backend()
        )
        self[kid] = final_key
        return final_key
