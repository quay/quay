from oauth.services.gitlab import GitLabOAuthService
from util.config.validators import BaseValidator, ConfigValidationException


class GitLabTriggerValidator(BaseValidator):
    name = "gitlab-trigger"

    @classmethod
    def validate(cls, validator_context):
        """
        Validates the OAuth credentials and API endpoint for a GitLab service.
        """
        config = validator_context.config
        url_scheme_and_hostname = validator_context.url_scheme_and_hostname
        client = validator_context.http_client

        github_config = config.get("GITLAB_TRIGGER_CONFIG")
        if not github_config:
            raise ConfigValidationException("Missing GitLab client id and client secret")

        endpoint = github_config.get("GITLAB_ENDPOINT")
        if endpoint:
            if endpoint.find("http://") != 0 and endpoint.find("https://") != 0:
                raise ConfigValidationException(
                    "GitLab Endpoint must start with http:// or https://"
                )

        if not github_config.get("CLIENT_ID"):
            raise ConfigValidationException("Missing Client ID")

        if not github_config.get("CLIENT_SECRET"):
            raise ConfigValidationException("Missing Client Secret")

        oauth = GitLabOAuthService(config, "GITLAB_TRIGGER_CONFIG")
        result = oauth.validate_client_id_and_secret(client, url_scheme_and_hostname)
        if not result:
            raise ConfigValidationException("Invalid client id or client secret")
