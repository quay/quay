import json
import logging
import time
import urllib.parse
from posixpath import join
from typing import Optional

import jwt
from authlib.jose import JsonWebKey, KeySet
from cachetools import TTLCache
from cachetools.func import lru_cache
from requests import request

from oauth.base import (
    OAuthEndpoint,
    OAuthExchangeCodeException,
    OAuthGetUserInfoException,
    OAuthService,
)
from oauth.login import OAuthLoginException
from oauth.login_utils import get_sub_username_email_from_token
from util.security.jwtutil import InvalidTokenError, decode

logger = logging.getLogger(__name__)


OIDC_WELLKNOWN = ".well-known/openid-configuration"
PUBLIC_KEY_CACHE_TTL = 3600  # 1 hour
ALLOWED_ALGORITHMS = ["RS256", "RS384"]
JWT_CLOCK_SKEW_SECONDS = 30


class PasswordGrantException(Exception):
    """
    Exception raised when authentication through Password Credentials Grant fails.
    """

    pass


class DeviceCodeException(Exception):
    """
    Exception raised when device code flow fails.
    """

    pass


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
        if self.config.get("OIDC_DISABLE_USER_ENDPOINT", False):
            return None
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

    def pkce_enabled(self) -> bool:
        return bool(self.config.get("USE_PKCE", False))

    def pkce_method(self) -> str:
        method = self.config.get("PKCE_METHOD", "S256")
        allowed_methods = {"S256", "plain"}
        if method not in allowed_methods:
            raise ValueError(f"Invalid PKCE method '{method}'. Must be one of: {allowed_methods}")
        return method

    def public_client(self) -> bool:
        return bool(self.config.get("PUBLIC_CLIENT", False))

    def exchange_code_for_tokens(
        self,
        app_config,
        http_client,
        code,
        redirect_suffix,
        code_verifier: Optional[str] = None,
    ):
        # Exchange the code for the access token and id_token
        try:
            extra_token_params = None
            if self.pkce_enabled() and code_verifier:
                extra_token_params = {"code_verifier": code_verifier}

            json_data = self.exchange_code(
                app_config,
                http_client,
                code,
                redirect_suffix=redirect_suffix,
                form_encode=self.requires_form_encoding(),
                extra_token_params=extra_token_params,
                omit_client_secret=self.public_client(),
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

    def exchange_code_for_login(
        self,
        app_config,
        http_client,
        code,
        redirect_suffix,
        code_verifier: Optional[str] = None,
    ):
        # Exchange the code for the access token and id_token
        id_token, access_token = self.exchange_code_for_tokens(
            app_config, http_client, code, redirect_suffix, code_verifier=code_verifier
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

        return get_sub_username_email_from_token(
            decoded_id_token, user_info, self, self._mailing, fetch_groups=True
        )

    @property
    def _issuer(self):
        # Read the issuer from the OIDC config, falling back to the configured OIDC server.
        issuer = self._oidc_config().get("issuer", self.config["OIDC_SERVER"])

        # If specified, use the overridden OIDC issuer.
        return self.config.get("OIDC_ISSUER", issuer)

    def get_issuer(self):
        return self._issuer

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

        discovery_url = join(oidc_server, OIDC_WELLKNOWN)
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

    def decode_user_jwt(self, token, options={}):
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

        key = ""
        if options.get("verify_signature", True):
            key = self._get_public_key(kid)

        try:
            return decode(
                token,
                key,
                algorithms=ALLOWED_ALGORITHMS,
                audience=self.client_id(),
                issuer=self._issuer,
                leeway=JWT_CLOCK_SKEW_SECONDS,
                options=dict(require=["iat", "exp"], **options),
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
                    options=dict(require=["iat", "exp"], **options),
                )
            except InvalidTokenError as ite:
                logger.warning(
                    "Could not decode token `%s` for OIDC: %s. Attempted again after "
                    + "retrieving public keys.",
                    token,
                    ite,
                )

                # Decode again with verify_signature=False, and log the decoded token to allow for easier debugging.
                nonverified = decode(
                    token,
                    None,  # No key needed for non-verified decode
                    algorithms=ALLOWED_ALGORITHMS,
                    audience=self.client_id(),
                    issuer=self._issuer,
                    leeway=JWT_CLOCK_SKEW_SECONDS,
                    options=dict(require=["iat", "exp"], verify_signature=False, **options),
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

    def password_grant_for_login(self, username, password):
        """
        OIDC authentication via Password Credentials Grant
        """
        if not username or not password:
            raise PasswordGrantException("Missing username or password")

        payload = {
            "grant_type": "password",
            "username": username,
            "password": password,
            "client_id": self.client_id(),
            "client_secret": self.client_secret(),
            "scope": " ".join(self.get_login_scopes()),
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        token_url = self.token_endpoint().to_url()
        response = self._http_client.post(token_url, data=payload, headers=headers, timeout=5)

        if response.status_code // 100 != 2:
            logger.debug("Got get_access_token response %s", response.text)
            raise PasswordGrantException(
                f"Got {response.status_code} response for code exchange: {response.text}"
            )

        json_data = response.json()
        if not json_data:
            raise PasswordGrantException("Got non-JSON response for password credentials grant")

        if not json_data.get("access_token", None):
            raise PasswordGrantException(
                "Failed to read access_token in response for password credentials grant"
            )

        return json_data

    def device_authorization_endpoint(self):
        """
        Returns the device authorization endpoint from OIDC discovery.
        If not available, constructs it from the authorization endpoint.
        """
        device_auth_endpoint = self._oidc_config().get("device_authorization_endpoint")
        if device_auth_endpoint:
            return OAuthEndpoint(device_auth_endpoint)

        # Fallback: construct from authorization endpoint (common pattern)
        auth_endpoint = self._oidc_config().get("authorization_endpoint", "")
        if auth_endpoint:
            # Replace /authorize with /devicecode (common Azure AD pattern)
            device_endpoint = auth_endpoint.replace("/authorize", "/devicecode")
            return OAuthEndpoint(device_endpoint)

        raise DeviceCodeException("Device authorization endpoint not available")

    def initiate_device_code_flow(self):
        """
        Initiates the device code flow by requesting device and user codes.
        Returns device code response with user_code, device_code, verification_uri, etc.
        """
        try:
            device_auth_url = self.device_authorization_endpoint().to_url()
        except DeviceCodeException as e:
            raise DeviceCodeException(f"Device code flow not supported: {str(e)}")

        payload = {
            "client_id": self.client_id(),
            "scope": " ".join(self.get_login_scopes()),
        }

        # Some providers require client_secret for device code flow
        if self.client_secret():
            payload["client_secret"] = self.client_secret()

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = self._http_client.post(
                device_auth_url, data=payload, headers=headers, timeout=10
            )

            if response.status_code != 200:
                logger.debug("Device code initiation failed: %s", response.text)
                raise DeviceCodeException(
                    f"Device code initiation failed with status {response.status_code}: {response.text}"
                )

            device_code_response = response.json()

            # Validate required fields
            required_fields = ["device_code", "user_code", "verification_uri"]
            missing_fields = [
                field for field in required_fields if field not in device_code_response
            ]
            if missing_fields:
                raise DeviceCodeException(
                    f"Missing required fields in device code response: {missing_fields}"
                )

            return device_code_response

        except Exception as e:
            if isinstance(e, DeviceCodeException):
                raise
            raise DeviceCodeException(f"Device code initiation request failed: {str(e)}")

    def poll_for_token(self, device_code, interval=5, max_attempts=60):
        """
        Polls the token endpoint for device code completion.
        Returns token response when user completes authentication.
        """
        token_url = self.token_endpoint().to_url()

        payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": self.client_id(),
            "device_code": device_code,
        }

        if self.client_secret():
            payload["client_secret"] = self.client_secret()

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        for attempt in range(max_attempts):
            try:
                response = self._http_client.post(
                    token_url, data=payload, headers=headers, timeout=10
                )

                if response.status_code == 200:
                    token_response = response.json()

                    # Validate we got the required tokens
                    if not token_response.get("access_token"):
                        raise DeviceCodeException("Missing access_token in response")

                    return token_response

                elif response.status_code == 400:
                    error_response = response.json()
                    error_code = error_response.get("error", "unknown_error")

                    if error_code == "authorization_pending":
                        # User hasn't completed auth yet, continue polling
                        if attempt < max_attempts - 1:  # Don't sleep on last attempt
                            time.sleep(interval)
                        continue
                    elif error_code == "slow_down":
                        # Provider requests slower polling
                        interval = min(interval + 1, 10)
                        if attempt < max_attempts - 1:
                            time.sleep(interval)
                        continue
                    elif error_code in ["access_denied", "expired_token"]:
                        # User denied or token expired
                        raise DeviceCodeException(f"Device code flow failed: {error_code}")
                    else:
                        # Other error
                        raise DeviceCodeException(f"Token polling failed: {error_code}")

                else:
                    raise DeviceCodeException(
                        f"Token polling failed with status {response.status_code}"
                    )

            except Exception as e:
                if isinstance(e, DeviceCodeException):
                    raise
                # Network error, wait and retry
                if attempt < max_attempts - 1:
                    time.sleep(interval)
                continue

        raise DeviceCodeException(
            "Device code flow timed out - user did not complete authentication"
        )


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
            keys = KeySet(
                _load_keys_from_url(
                    keys_url, verify=not self._login_service.config.get("DEBUGGING", False)
                )
            )
        except Exception as ex:
            logger.exception("Exception loading public key")
            raise PublicKeyLoadException(str(ex))

        # Find the matching key.
        try:
            key_found = keys.find_by_kid(kid)
        except ValueError:
            raise PublicKeyLoadException("Public key %s not found" % kid)

        if key_found.kty != "RSA":
            raise PublicKeyLoadException("No RSA form of public key %s not found" % kid)

        # Eyy, no more exporting/importing keys from PyCrypto to cryptography's format...
        rsa_key = key_found.as_key()
        self[kid] = rsa_key
        return rsa_key


def _load_keys_from_url(url, verify=True):
    """
    Expects something on this form:
        {"keys":
            [
                {
                    "kty":"EC",
                    "crv":"P-256",
                    "x":"MKBCTNIcKUSDii11ySs3526iDZ8AiTo7Tu6KPAqv7D4",
                    "y":"4Etl6SRW2YiLUrN5vfvVHuhp7x8PxltmWWlbbM4IFyM",
                    "use":"enc",
                    "kid":"1"
                },
                {
                    "kty":"RSA",
                    "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFb....."
                    "e":"AQAB",
                    "kid":"2011-04-29"
                }
            ]
        }
    """

    keys = []
    r = request("GET", url, allow_redirects=True, verify=verify)
    if r.status_code == 200:
        keys_dict = json.loads(r.text)
        for key_spec in keys_dict["keys"]:
            key = JsonWebKey.import_key(key_spec)
            keys.append(key)
    else:
        raise Exception("Error loading JWK set - HTTP GET error: %s" % r.status_code)

    return keys
