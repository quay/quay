from typing import Optional
from oauth.services.github import GithubOAuthService
from util.config.validators import BaseValidator, ConfigValidationException


class BaseGitHubValidator(BaseValidator):
    name = None  # type: Optional[str]
    config_key = None  # type: Optional[str]

    @classmethod
    def validate(cls, validator_context):
        """
        Validates the OAuth credentials and API endpoint for a Github service.
        """
        config = validator_context.config
        client = validator_context.http_client
        url_scheme_and_hostname = validator_context.url_scheme_and_hostname

        github_config = config.get(cls.config_key)
        if not github_config:
            raise ConfigValidationException("Missing GitHub client id and client secret")

        endpoint = github_config.get("GITHUB_ENDPOINT")
        if not endpoint:
            raise ConfigValidationException("Missing GitHub Endpoint")

        if endpoint.find("http://") != 0 and endpoint.find("https://") != 0:
            raise ConfigValidationException("Github Endpoint must start with http:// or https://")

        if not github_config.get("CLIENT_ID"):
            raise ConfigValidationException("Missing Client ID")

        if not github_config.get("CLIENT_SECRET"):
            raise ConfigValidationException("Missing Client Secret")

        if github_config.get("ORG_RESTRICT") and not github_config.get("ALLOWED_ORGANIZATIONS"):
            raise ConfigValidationException(
                "Organization restriction must have at least one allowed " + "organization"
            )

        oauth = GithubOAuthService(config, cls.config_key)
        result = oauth.validate_client_id_and_secret(client, url_scheme_and_hostname)
        if not result:
            raise ConfigValidationException("Invalid client id or client secret")

        if github_config.get("ALLOWED_ORGANIZATIONS"):
            for org_id in github_config.get("ALLOWED_ORGANIZATIONS"):
                if not oauth.validate_organization(org_id, client):
                    raise ConfigValidationException("Invalid organization: %s" % org_id)


class GitHubLoginValidator(BaseGitHubValidator):
    name = "github-login"
    config_key = "GITHUB_LOGIN_CONFIG"


class GitHubTriggerValidator(BaseGitHubValidator):
    name = "github-trigger"
    config_key = "GITHUB_TRIGGER_CONFIG"
