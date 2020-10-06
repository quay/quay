from util.config.validators import BaseValidator, ConfigValidationException
from oauth.loginmanager import OAuthLoginManager
from oauth.oidc import OIDCLoginService


class AccessSettingsValidator(BaseValidator):
    name = "access"

    @classmethod
    def validate(cls, validator_context):
        config = validator_context.config
        client = validator_context.http_client

        if not config.get("FEATURE_DIRECT_LOGIN", True):
            # Make sure we have at least one OIDC enabled.
            github_login = config.get("FEATURE_GITHUB_LOGIN", False)
            google_login = config.get("FEATURE_GOOGLE_LOGIN", False)
            openshift_login = config.get("FEATURE_OPENSHIFT_LOGIN", False)

            login_manager = OAuthLoginManager(config, client=client)
            custom_oidc = [s for s in login_manager.services if isinstance(s, OIDCLoginService)]

            if not any([github_login, google_login, openshift_login]) and not custom_oidc:
                msg = "Cannot disable credentials login to UI without configured OIDC service"
                raise ConfigValidationException(msg)

        if not config.get("FEATURE_USER_CREATION", True) and config.get(
            "FEATURE_INVITE_ONLY_USER_CREATION", False
        ):
            msg = "Invite only user creation requires user creation to be enabled"
            raise ConfigValidationException(msg)
