from oauth.services.google import GoogleOAuthService
from util.config.validators import BaseValidator, ConfigValidationException


class GoogleLoginValidator(BaseValidator):
    name = "google-login"

    @classmethod
    def validate(cls, validator_context):
        """
        Validates the Google Login client ID and secret.
        """
        config = validator_context.config
        client = validator_context.http_client
        url_scheme_and_hostname = validator_context.url_scheme_and_hostname

        google_login_config = config.get("GOOGLE_LOGIN_CONFIG")
        if not google_login_config:
            raise ConfigValidationException("Missing client ID and client secret")

        if not google_login_config.get("CLIENT_ID"):
            raise ConfigValidationException("Missing Client ID")

        if not google_login_config.get("CLIENT_SECRET"):
            raise ConfigValidationException("Missing Client Secret")

        oauth = GoogleOAuthService(config, "GOOGLE_LOGIN_CONFIG")
        result = oauth.validate_client_id_and_secret(client, url_scheme_and_hostname)
        if not result:
            raise ConfigValidationException("Invalid client id or client secret")
