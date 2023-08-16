from oauth.oidc import OIDCLoginService
from oauth.services.github import GithubOAuthService
from oauth.services.google import GoogleOAuthService
from oauth.services.rhsso import RHSSOOAuthService

CUSTOM_LOGIN_SERVICES = {
    "GITHUB_LOGIN_CONFIG": GithubOAuthService,
    "GOOGLE_LOGIN_CONFIG": GoogleOAuthService,
}

PREFIX_BLACKLIST = ["ldap", "jwt", "keystone"]


class OAuthLoginManager(object):
    """
    Helper class which manages all registered OAuth login services.
    """

    def __init__(self, config, client=None):
        self.services = []

        # Register the endpoints for each of the OAuth login services.
        for key in list(config.keys()):
            # All keys which end in _LOGIN_CONFIG setup a login service.
            if key.endswith("_LOGIN_CONFIG"):
                if key in CUSTOM_LOGIN_SERVICES:
                    custom_service = CUSTOM_LOGIN_SERVICES[key](config, key)
                    if custom_service.login_enabled(config):
                        self.services.append(custom_service)
                else:
                    prefix = key[: -len("_LOGIN_CONFIG")].lower()
                    if prefix in PREFIX_BLACKLIST:
                        raise Exception("Cannot use reserved config name %s" % key)
                    if prefix == "rhsso":
                        self.services.append(RHSSOOAuthService(config, key, client=client))
                    else:
                        self.services.append(OIDCLoginService(config, key, client=client))

    def get_service(self, service_id):
        for service in self.services:
            if service.service_id() == service_id:
                return service

    def get_service_by_issuer(self, issuer):
        for service in self.services:

            if not hasattr(service, "get_issuer"):
                continue

            if not service.get_issuer:
                continue

            config_issuer = service.get_issuer()

            if config_issuer.rstrip("/") == issuer.rstrip("/"):
                return service

        return None
