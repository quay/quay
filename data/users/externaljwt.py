import logging
import json
import os

from data.users.federated import FederatedUsers, UserInformation
from util.security import jwtutil


logger = logging.getLogger(__name__)


class ExternalJWTAuthN(FederatedUsers):
    """
    Delegates authentication to a REST endpoint that returns JWTs.
    """

    PUBLIC_KEY_FILENAME = "jwt-authn.cert"

    def __init__(
        self,
        verify_url,
        query_url,
        getuser_url,
        issuer,
        override_config_dir,
        http_client,
        max_fresh_s,
        public_key_path=None,
        requires_email=True,
    ):
        super(ExternalJWTAuthN, self).__init__("jwtauthn", requires_email)
        self.verify_url = verify_url
        self.query_url = query_url
        self.getuser_url = getuser_url

        self.issuer = issuer
        self.client = http_client
        self.max_fresh_s = max_fresh_s
        self.requires_email = requires_email

        default_key_path = os.path.join(override_config_dir, ExternalJWTAuthN.PUBLIC_KEY_FILENAME)
        public_key_path = public_key_path or default_key_path
        if not os.path.exists(public_key_path):
            error_message = 'JWT Authentication public key file "%s" not found' % public_key_path

            raise Exception(error_message)

        self.public_key_path = public_key_path

        with open(public_key_path, mode="rb") as public_key_file:
            self.public_key = public_key_file.read()

    def has_password_set(self, username):
        return True

    def ping(self):
        result = self.client.get(self.getuser_url, timeout=2)
        # We expect a 401 or 403 of some kind, since we explicitly don't send an auth header
        if result.status_code // 100 != 4:
            return (False, result.text or "Could not reach JWT authn endpoint")

        return (True, None)

    def get_user(self, username_or_email):
        if self.getuser_url is None:
            return (None, "No endpoint defined for retrieving user")

        (payload, err_msg) = self._execute_call(
            self.getuser_url, "quay.io/jwtauthn/getuser", params=dict(username=username_or_email)
        )
        if err_msg is not None:
            return (None, err_msg)

        if not "sub" in payload:
            raise Exception("Missing sub field in JWT")

        if self.requires_email and not "email" in payload:
            raise Exception("Missing email field in JWT")

        # Parse out the username and email.
        user_info = UserInformation(
            username=payload["sub"], email=payload.get("email"), id=payload["sub"]
        )
        return (user_info, None)

    def query_users(self, query, limit=20):
        if self.query_url is None:
            return (None, self.federated_service, "No endpoint defined for querying users")

        (payload, err_msg) = self._execute_call(
            self.query_url, "quay.io/jwtauthn/query", params=dict(query=query, limit=limit)
        )
        if err_msg is not None:
            return (None, self.federated_service, err_msg)

        query_results = []
        for result in payload["results"][0:limit]:
            user_info = UserInformation(
                username=result["username"], email=result.get("email"), id=result["username"]
            )
            query_results.append(user_info)

        return (query_results, self.federated_service, None)

    def verify_credentials(self, username_or_email, password):
        (payload, err_msg) = self._execute_call(
            self.verify_url, "quay.io/jwtauthn", auth=(username_or_email, password)
        )
        if err_msg is not None:
            return (None, err_msg)

        if not "sub" in payload:
            raise Exception("Missing sub field in JWT")

        if self.requires_email and not "email" in payload:
            raise Exception("Missing email field in JWT")

        user_info = UserInformation(
            username=payload["sub"], email=payload.get("email"), id=payload["sub"]
        )
        return (user_info, None)

    def _execute_call(self, url, aud, auth=None, params=None):
        """
        Executes a call to the external JWT auth provider.
        """
        result = self.client.get(url, timeout=2, auth=auth, params=params)
        if result.status_code != 200:
            return (None, result.text or "Could not make JWT auth call")

        try:
            result_data = json.loads(result.text)
        except ValueError:
            raise Exception("Returned JWT body for url %s does not contain JSON", url)

        # Load the JWT returned.
        encoded = result_data.get("token", "")
        exp_limit_options = jwtutil.exp_max_s_option(self.max_fresh_s)
        try:
            payload = jwtutil.decode(
                encoded,
                self.public_key,
                algorithms=["RS256"],
                audience=aud,
                issuer=self.issuer,
                options=exp_limit_options,
            )
            return (payload, None)
        except jwtutil.InvalidTokenError:
            logger.exception("Exception when decoding returned JWT for url %s", url)
            return (None, "Exception when decoding returned JWT")
