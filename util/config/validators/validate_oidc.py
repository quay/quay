from oauth.loginmanager import OAuthLoginManager
from oauth.oidc import OIDCLoginService, DiscoveryFailureException
from util.config.validators import BaseValidator, ConfigValidationException


class OIDCLoginValidator(BaseValidator):
    name = "oidc-login"

    @classmethod
    def validate(cls, validator_context):
        config = validator_context.config
        client = validator_context.http_client

        login_manager = OAuthLoginManager(config, client=client)
        for service in login_manager.services:
            if not isinstance(service, OIDCLoginService):
                continue

            if service.config.get("OIDC_SERVER") is None:
                msg = "Missing OIDC_SERVER on OIDC service %s" % service.service_id()
                raise ConfigValidationException(msg)

            if service.config.get("CLIENT_ID") is None:
                msg = "Missing CLIENT_ID on OIDC service %s" % service.service_id()
                raise ConfigValidationException(msg)

            if service.config.get("CLIENT_SECRET") is None:
                msg = "Missing CLIENT_SECRET on OIDC service %s" % service.service_id()
                raise ConfigValidationException(msg)

            try:
                if not service.validate():
                    msg = "Could not validate OIDC service %s" % service.service_id()
                    raise ConfigValidationException(msg)
            except DiscoveryFailureException as dfe:
                msg = "Could not validate OIDC service %s: %s" % (service.service_id(), str(dfe))
                raise ConfigValidationException(msg)
