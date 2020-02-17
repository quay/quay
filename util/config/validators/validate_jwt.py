import os
from data.users.externaljwt import ExternalJWTAuthN
from util.config.validators import BaseValidator, ConfigValidationException


class JWTAuthValidator(BaseValidator):
    name = "jwt"

    @classmethod
    def validate(cls, validator_context, public_key_path=None):
        """
        Validates the JWT authentication system.
        """
        config = validator_context.config
        http_client = validator_context.http_client
        jwt_auth_max = validator_context.jwt_auth_max
        config_provider = validator_context.config_provider

        if config.get("AUTHENTICATION_TYPE", "Database") != "JWT":
            return

        verify_endpoint = config.get("JWT_VERIFY_ENDPOINT")
        query_endpoint = config.get("JWT_QUERY_ENDPOINT", None)
        getuser_endpoint = config.get("JWT_GETUSER_ENDPOINT", None)

        issuer = config.get("JWT_AUTH_ISSUER")

        if not verify_endpoint:
            raise ConfigValidationException("Missing JWT Verification endpoint")

        if not issuer:
            raise ConfigValidationException("Missing JWT Issuer ID")

        override_config_directory = config_provider.get_config_dir_path()

        # Try to instatiate the JWT authentication mechanism. This will raise an exception if
        # the key cannot be found.
        users = ExternalJWTAuthN(
            verify_endpoint,
            query_endpoint,
            getuser_endpoint,
            issuer,
            override_config_directory,
            http_client,
            jwt_auth_max,
            public_key_path=public_key_path,
            requires_email=config.get("FEATURE_MAILING", True),
        )

        # Verify that we can reach the jwt server
        (result, err_msg) = users.ping()
        if not result:
            msg = (
                "Verification of JWT failed: %s. \n\nWe cannot reach the JWT server"
                + "OR JWT auth is misconfigured"
            ) % err_msg
            raise ConfigValidationException(msg)
