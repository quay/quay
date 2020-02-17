from util.config.validators import BaseValidator, ConfigValidationException


class AppTokenAuthValidator(BaseValidator):
    name = "apptoken-auth"

    @classmethod
    def validate(cls, validator_context):
        config = validator_context.config

        if config.get("AUTHENTICATION_TYPE", "Database") != "AppToken":
            return

        # Ensure that app tokens are enabled, as they are required.
        if not config.get("FEATURE_APP_SPECIFIC_TOKENS", False):
            msg = "Application token support must be enabled to use External Application Token auth"
            raise ConfigValidationException(msg)

        # Ensure that direct login is disabled.
        if config.get("FEATURE_DIRECT_LOGIN", True):
            msg = "Direct login must be disabled to use External Application Token auth"
            raise ConfigValidationException(msg)
