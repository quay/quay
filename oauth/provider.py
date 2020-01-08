# Ported to Python 3
# Originally from https://github.com/DeprecatedCode/oauth2lib/blob/d161b010f8a596826050a09e5e94d59443cc12d9/oauth2lib/provider.py

import json
import logging
from requests import Response
from io import StringIO

try:
    from werkzeug.exceptions import Unauthorized
except ImportError:
    Unauthorized = Exception

from oauth import utils


class Provider(object):
    """Base provider class for different types of OAuth 2.0 providers."""

    def _handle_exception(self, exc):
        """Handle an internal exception that was caught and suppressed.

        :param exc: Exception to process.
        :type exc: Exception
        """
        logger = logging.getLogger(__name__)
        logger.exception(exc)

    def _make_response(self, body="", headers=None, status_code=200):
        """Return a response object from the given parameters.

        :param body: Buffer/string containing the response body.
        :type body: str
        :param headers: Dict of headers to include in the requests.
        :type headers: dict
        :param status_code: HTTP status code.
        :type status_code: int
        :rtype: requests.Response
        """
        res = Response()
        res.status_code = status_code
        if headers is not None:
            res.headers.update(headers)
        res.raw = StringIO(body)
        return res

    def _make_redirect_error_response(self, redirect_uri, err):
        """Return a HTTP 302 redirect response object containing the error.

        :param redirect_uri: Client redirect URI.
        :type redirect_uri: str
        :param err: OAuth error message.
        :type err: str
        :rtype: requests.Response
        """
        params = {"error": err, "response_type": None, "client_id": None, "redirect_uri": None}
        redirect = utils.build_url(redirect_uri, params)
        return self._make_response(headers={"Location": redirect}, status_code=302)

    def _make_json_response(self, data, headers=None, status_code=200):
        """Return a response object from the given JSON data.

        :param data: Data to JSON-encode.
        :type data: mixed
        :param headers: Dict of headers to include in the requests.
        :type headers: dict
        :param status_code: HTTP status code.
        :type status_code: int
        :rtype: requests.Response
        """
        response_headers = {}
        if headers is not None:
            response_headers.update(headers)
        response_headers["Content-Type"] = "application/json;charset=UTF-8"
        response_headers["Cache-Control"] = "no-store"
        response_headers["Pragma"] = "no-cache"
        return self._make_response(json.dumps(data), response_headers, status_code)

    def _make_json_error_response(self, err):
        """Return a JSON-encoded response object representing the error.

        :param err: OAuth error message.
        :type err: str
        :rtype: requests.Response
        """
        return self._make_json_response({"error": err}, status_code=400)

    def _invalid_redirect_uri_response(self):
        """What to return when the redirect_uri parameter is missing.

        :rtype: requests.Response
        """
        return self._make_json_error_response("invalid_request")


class AuthorizationProvider(Provider):
    """OAuth 2.0 authorization provider. This class manages authorization
    codes and access tokens. Certain methods MUST be overridden in a
    subclass, thus this class cannot be directly used as a provider.

    These are the methods that must be implemented in a subclass:

        validate_client_id(self, client_id)
            # Return True or False

        validate_client_secret(self, client_id, client_secret)
            # Return True or False

        validate_scope(self, client_id, scope)
            # Return True or False

        validate_redirect_uri(self, client_id, redirect_uri)
            # Return True or False

        validate_access(self)  # Use this to validate your app session user
            # Return True or False

        from_authorization_code(self, client_id, code, scope)
            # Return mixed data or None on invalid

        from_refresh_token(self, client_id, refresh_token, scope)
            # Return mixed data or None on invalid

        persist_authorization_code(self, client_id, code, scope)
            # Return value ignored

        persist_token_information(self, client_id, scope, access_token,
                                  token_type, expires_in, refresh_token,
                                  data)
            # Return value ignored

        discard_authorization_code(self, client_id, code)
            # Return value ignored

        discard_refresh_token(self, client_id, refresh_token)
            # Return value ignored

    Optionally, the following may be overridden to acheive desired behavior:

        @property
        token_length(self)

        @property
        token_type(self)

        @property
        token_expires_in(self)

        generate_authorization_code(self)

        generate_access_token(self)

        generate_refresh_token(self)

    """

    @property
    def token_length(self):
        """Property method to get the length used to generate tokens.

        :rtype: int
        """
        return 40

    @property
    def token_type(self):
        """Property method to get the access token type.

        :rtype: str
        """
        return "Bearer"

    @property
    def token_expires_in(self):
        """Property method to get the token expiration time in seconds.

        :rtype: int
        """
        return 3600

    def generate_authorization_code(self):
        """Generate a random authorization code.

        :rtype: str
        """
        return utils.random_ascii_string(self.token_length)

    def generate_access_token(self):
        """Generate a random access token.

        :rtype: str
        """
        return utils.random_ascii_string(self.token_length)

    def generate_refresh_token(self):
        """Generate a random refresh token.

        :rtype: str
        """
        return utils.random_ascii_string(self.token_length)

    def get_authorization_code(self, response_type, client_id, redirect_uri, **params):
        """Generate authorization code HTTP response.

        :param response_type: Desired response type. Must be exactly "code".
        :type response_type: str
        :param client_id: Client ID.
        :type client_id: str
        :param redirect_uri: Client redirect URI.
        :type redirect_uri: str
        :rtype: requests.Response
        """

        # Ensure proper response_type
        if response_type != "code":
            err = "unsupported_response_type"
            return self._make_redirect_error_response(redirect_uri, err)

        # Check redirect URI
        is_valid_redirect_uri = self.validate_redirect_uri(client_id, redirect_uri)
        if not is_valid_redirect_uri:
            return self._invalid_redirect_uri_response()

        # Check conditions
        is_valid_client_id = self.validate_client_id(client_id)
        is_valid_access = self.validate_access()
        scope = params.get("scope", "")
        is_valid_scope = self.validate_scope(client_id, scope)

        # Return proper error responses on invalid conditions
        if not is_valid_client_id:
            err = "unauthorized_client"
            return self._make_redirect_error_response(redirect_uri, err)

        if not is_valid_access:
            err = "access_denied"
            return self._make_redirect_error_response(redirect_uri, err)

        if not is_valid_scope:
            err = "invalid_scope"
            return self._make_redirect_error_response(redirect_uri, err)

        # Generate authorization code
        code = self.generate_authorization_code()

        # Save information to be used to validate later requests
        self.persist_authorization_code(client_id=client_id, code=code, scope=scope)

        # Return redirection response
        params.update(
            {"code": code, "response_type": None, "client_id": None, "redirect_uri": None}
        )
        redirect = utils.build_url(redirect_uri, params)
        return self._make_response(headers={"Location": redirect}, status_code=302)

    def refresh_token(self, grant_type, client_id, client_secret, refresh_token, **params):
        """Generate access token HTTP response from a refresh token.

        :param grant_type: Desired grant type. Must be "refresh_token".
        :type grant_type: str
        :param client_id: Client ID.
        :type client_id: str
        :param client_secret: Client secret.
        :type client_secret: str
        :param refresh_token: Refresh token.
        :type refresh_token: str
        :rtype: requests.Response
        """

        # Ensure proper grant_type
        if grant_type != "refresh_token":
            return self._make_json_error_response("unsupported_grant_type")

        # Check conditions
        is_valid_client_id = self.validate_client_id(client_id)
        is_valid_client_secret = self.validate_client_secret(client_id, client_secret)
        scope = params.get("scope", "")
        is_valid_scope = self.validate_scope(client_id, scope)
        data = self.from_refresh_token(client_id, refresh_token, scope)
        is_valid_refresh_token = data is not None

        # Return proper error responses on invalid conditions
        if not (is_valid_client_id and is_valid_client_secret):
            return self._make_json_error_response("invalid_client")

        if not is_valid_scope:
            return self._make_json_error_response("invalid_scope")

        if not is_valid_refresh_token:
            return self._make_json_error_response("invalid_grant")

        # Discard original refresh token
        self.discard_refresh_token(client_id, refresh_token)

        # Generate access tokens once all conditions have been met
        access_token = self.generate_access_token()
        token_type = self.token_type
        expires_in = self.token_expires_in
        refresh_token = self.generate_refresh_token()

        # Save information to be used to validate later requests
        self.persist_token_information(
            client_id=client_id,
            scope=scope,
            access_token=access_token,
            token_type=token_type,
            expires_in=expires_in,
            refresh_token=refresh_token,
            data=data,
        )

        # Return json response
        return self._make_json_response(
            {
                "access_token": access_token,
                "token_type": token_type,
                "expires_in": expires_in,
                "refresh_token": refresh_token,
            }
        )

    def get_token(self, grant_type, client_id, client_secret, redirect_uri, code, **params):
        """Generate access token HTTP response.

        :param grant_type: Desired grant type. Must be "authorization_code".
        :type grant_type: str
        :param client_id: Client ID.
        :type client_id: str
        :param client_secret: Client secret.
        :type client_secret: str
        :param redirect_uri: Client redirect URI.
        :type redirect_uri: str
        :param code: Authorization code.
        :type code: str
        :rtype: requests.Response
        """

        # Ensure proper grant_type
        if grant_type != "authorization_code":
            return self._make_json_error_response("unsupported_grant_type")

        # Check conditions
        is_valid_client_id = self.validate_client_id(client_id)
        is_valid_client_secret = self.validate_client_secret(client_id, client_secret)
        is_valid_redirect_uri = self.validate_redirect_uri(client_id, redirect_uri)

        scope = params.get("scope", "")
        is_valid_scope = self.validate_scope(client_id, scope)
        data = self.from_authorization_code(client_id, code, scope)
        is_valid_grant = data is not None

        # Return proper error responses on invalid conditions
        if not (is_valid_client_id and is_valid_client_secret):
            return self._make_json_error_response("invalid_client")

        if not is_valid_grant or not is_valid_redirect_uri:
            return self._make_json_error_response("invalid_grant")

        if not is_valid_scope:
            return self._make_json_error_response("invalid_scope")

        # Discard original authorization code
        self.discard_authorization_code(client_id, code)

        # Generate access tokens once all conditions have been met
        access_token = self.generate_access_token()
        token_type = self.token_type
        expires_in = self.token_expires_in
        refresh_token = self.generate_refresh_token()

        # Save information to be used to validate later requests
        self.persist_token_information(
            client_id=client_id,
            scope=scope,
            access_token=access_token,
            token_type=token_type,
            expires_in=expires_in,
            refresh_token=refresh_token,
            data=data,
        )

        # Return json response
        return self._make_json_response(
            {
                "access_token": access_token,
                "token_type": token_type,
                "expires_in": expires_in,
                "refresh_token": refresh_token,
            }
        )

    def get_authorization_code_from_uri(self, uri):
        """Get authorization code response from a URI. This method will
        ignore the domain and path of the request, instead
        automatically parsing the query string parameters.

        :param uri: URI to parse for authorization information.
        :type uri: str
        :rtype: requests.Response
        """
        params = utils.url_query_params(uri)
        try:
            if "response_type" not in params:
                raise TypeError("Missing parameter response_type in URL query")

            if "client_id" not in params:
                raise TypeError("Missing parameter client_id in URL query")

            if "redirect_uri" not in params:
                raise TypeError("Missing parameter redirect_uri in URL query")

            return self.get_authorization_code(**params)
        except TypeError as exc:
            self._handle_exception(exc)

            # Catch missing parameters in request
            err = "invalid_request"
            if "redirect_uri" in params:
                u = params["redirect_uri"]
                return self._make_redirect_error_response(u, err)
            else:
                return self._invalid_redirect_uri_response()
        except StandardError as exc:
            self._handle_exception(exc)

            # Catch all other server errors
            err = "server_error"
            u = params["redirect_uri"]
            return self._make_redirect_error_response(u, err)

    def get_token_from_post_data(self, data):
        """Get a token response from POST data.

        :param data: POST data containing authorization information.
        :type data: dict
        :rtype: requests.Response
        """
        try:
            # Verify OAuth 2.0 Parameters
            for x in ["grant_type", "client_id", "client_secret"]:
                if not data.get(x):
                    raise TypeError("Missing required OAuth 2.0 POST param: {0}".format(x))

            # Handle get token from refresh_token
            if "refresh_token" in data:
                return self.refresh_token(**data)

            # Handle get token from authorization code
            for x in ["redirect_uri", "code"]:
                if not data.get(x):
                    raise TypeError("Missing required OAuth 2.0 POST param: {0}".format(x))
            return self.get_token(**data)
        except TypeError as exc:
            self._handle_exception(exc)

            # Catch missing parameters in request
            return self._make_json_error_response("invalid_request")
        except StandardError as exc:
            self._handle_exception(exc)

            # Catch all other server errors
            return self._make_json_error_response("server_error")

    def validate_client_id(self, client_id):
        raise NotImplementedError("Subclasses must implement " "validate_client_id.")

    def validate_client_secret(self, client_id, client_secret):
        raise NotImplementedError("Subclasses must implement " "validate_client_secret.")

    def validate_redirect_uri(self, client_id, redirect_uri):
        raise NotImplementedError("Subclasses must implement " "validate_redirect_uri.")

    def validate_scope(self, client_id, scope):
        raise NotImplementedError("Subclasses must implement " "validate_scope.")

    def validate_access(self):
        raise NotImplementedError("Subclasses must implement " "validate_access.")

    def from_authorization_code(self, client_id, code, scope):
        raise NotImplementedError("Subclasses must implement " "from_authorization_code.")

    def from_refresh_token(self, client_id, refresh_token, scope):
        raise NotImplementedError("Subclasses must implement " "from_refresh_token.")

    def persist_authorization_code(self, client_id, code, scope):
        raise NotImplementedError("Subclasses must implement " "persist_authorization_code.")

    def persist_token_information(
        self, client_id, scope, access_token, token_type, expires_in, refresh_token, data
    ):
        raise NotImplementedError("Subclasses must implement " "persist_token_information.")

    def discard_authorization_code(self, client_id, code):
        raise NotImplementedError("Subclasses must implement " "discard_authorization_code.")

    def discard_refresh_token(self, client_id, refresh_token):
        raise NotImplementedError("Subclasses must implement " "discard_refresh_token.")


class OAuthError(Unauthorized):
    """OAuth error, including the OAuth error reason."""

    def __init__(self, reason, *args, **kwargs):
        self.reason = reason
        super(OAuthError, self).__init__(*args, **kwargs)


class ResourceAuthorization(object):
    """A class containing an OAuth 2.0 authorization."""

    is_oauth = False
    is_valid = None
    token = None
    client_id = None
    expires_in = None
    error = None

    def raise_error_if_invalid(self):
        if not self.is_valid:
            raise OAuthError(self.error, "OAuth authorization error")


class ResourceProvider(Provider):
    """OAuth 2.0 resource provider. This class provides an interface
    to validate an incoming request and authenticate resource access.
    Certain methods MUST be overridden in a subclass, thus this
    class cannot be directly used as a resource provider.

    These are the methods that must be implemented in a subclass:

        get_authorization_header(self)
            # Return header string for key "Authorization" or None

        validate_access_token(self, access_token, authorization)
            # Set is_valid=True, client_id, and expires_in attributes
            #   on authorization if authorization was successful.
            # Return value is ignored
    """

    @property
    def authorization_class(self):
        return ResourceAuthorization

    def get_authorization(self):
        """Get authorization object representing status of authentication."""
        auth = self.authorization_class()
        header = self.get_authorization_header()
        if not header or not header.split:
            return auth
        header = header.split()
        if len(header) > 1 and header[0] == "Bearer":
            auth.is_oauth = True
            access_token = header[1]
            self.validate_access_token(access_token, auth)
            if not auth.is_valid:
                auth.error = "access_denied"
        return auth

    def get_authorization_header(self):
        raise NotImplementedError("Subclasses must implement " "get_authorization_header.")

    def validate_access_token(self, access_token, authorization):
        raise NotImplementedError("Subclasses must implement " "validate_token.")
