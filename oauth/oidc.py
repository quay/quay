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
from oauth.login_utils import get_jwt_issuer, get_sub_username_email_from_token
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

        self._validate_multi_config()

    def _validate_multi_config(self):
        issuer = self.config.get("OIDC_ISSUER")
        if issuer is not None and not isinstance(issuer, str):
            raise ValueError(f"OIDC_ISSUER must be a string, got {type(issuer).__name__}")

        for field in ("OIDC_ISSUERS", "OIDC_AUDIENCES", "OIDC_ALLOWED_CLIENTS"):
            value = self.config.get(field)
            if value is None:
                continue
            if not isinstance(value, list):
                raise ValueError(f"{field} must be a list, got {type(value).__name__}")
            if len(value) == 0:
                raise ValueError(f"{field} must not be empty")
            if not all(isinstance(item, str) for item in value):
                raise ValueError(f"{field} must contain only strings")

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

    @property
    def _issuers(self):
        issuers_list = self.config.get("OIDC_ISSUERS")
        if issuers_list:
            if self.config.get("OIDC_ISSUER"):
                logger.warning(
                    "Both OIDC_ISSUER and OIDC_ISSUERS configured; OIDC_ISSUERS takes precedence"
                )
            return issuers_list

        single_issuer = self.config.get("OIDC_ISSUER")
        if single_issuer:
            return [single_issuer]

        single_issuer = self._issuer
        return [single_issuer] if single_issuer else []

    def get_issuers(self):
        return self._issuers

    @property
    def _audiences(self):
        audiences_list = self.config.get("OIDC_AUDIENCES", [])
        client_id = self.client_id()
        if not audiences_list:
            return [client_id] if client_id else []
        if client_id and client_id not in audiences_list:
            return audiences_list + [client_id]
        return audiences_list

    @property
    def allowed_clients(self):
        return self.config.get("OIDC_ALLOWED_CLIENTS")

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
        headers = jwt.get_unverified_header(token)
        kid = headers.get("kid", None)
        if kid is None:
            raise InvalidTokenError("Missing `kid` header")

        audiences = self._audiences
        issuers = self._issuers

        effective_audience = None if options.get("verify_aud") is False else audiences

        token_issuer = get_jwt_issuer(token)

        if options.get("verify_iss", True) and token_issuer and issuers:
            normalized_issuers = [i.rstrip("/") for i in issuers]
            if token_issuer.rstrip("/") not in normalized_issuers:
                raise InvalidTokenError(
                    f"Issuer '{token_issuer}' not in configured issuers: {issuers}"
                )

        effective_issuer = token_issuer if token_issuer else (issuers[0] if issuers else None)

        logger.debug(
            "Using key `%s`, attempting to decode token with aud `%s` and iss `%s`",
            kid,
            effective_audience,
            effective_issuer,
        )

        key = ""
        if options.get("verify_signature", True):
            key = self._get_public_key(kid)

        decode_kwargs = dict(
            algorithms=ALLOWED_ALGORITHMS,
            issuer=effective_issuer,
            leeway=JWT_CLOCK_SKEW_SECONDS,
            options=dict(require=["iat", "exp"], **options),
        )
        if effective_audience is not None:
            decode_kwargs["audience"] = effective_audience

        try:
            return decode(token, key, **decode_kwargs)
        except InvalidTokenError as ite:
            logger.warning(
                "Could not decode token for OIDC: %s. Will attempt again after "
                "retrieving public keys.",
                ite,
            )

            try:
                return decode(
                    token,
                    self._get_public_key(kid, force_refresh=True),
                    **decode_kwargs,
                )
            except InvalidTokenError as ite:
                logger.warning(
                    "Could not decode token for OIDC: %s. Attempted again after "
                    "retrieving public keys.",
                    ite,
                )

                nonverified_kwargs = dict(decode_kwargs)
                nonverified_opts = dict(nonverified_kwargs.get("options", {}))
                nonverified_opts["verify_signature"] = False
                nonverified_kwargs["options"] = nonverified_opts
                nonverified = decode(token, None, **nonverified_kwargs)
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
