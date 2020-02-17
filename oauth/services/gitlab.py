from oauth.base import OAuthService, OAuthEndpoint
from util import slash_join


class GitLabOAuthService(OAuthService):
    def __init__(self, config, key_name):
        super(GitLabOAuthService, self).__init__(config, key_name)

    def service_id(self):
        return "gitlab"

    def service_name(self):
        return "GitLab"

    def _endpoint(self):
        return self.config.get("GITLAB_ENDPOINT", "https://gitlab.com")

    def user_endpoint(self):
        raise NotImplementedError

    def api_endpoint(self):
        return self._endpoint()

    def get_public_url(self, suffix):
        return slash_join(self._endpoint(), suffix)

    def authorize_endpoint(self):
        return OAuthEndpoint(slash_join(self._endpoint(), "/oauth/authorize"))

    def token_endpoint(self):
        return OAuthEndpoint(slash_join(self._endpoint(), "/oauth/token"))

    def validate_client_id_and_secret(self, http_client, url_scheme_and_hostname):
        # We validate the client ID and secret by hitting the OAuth token exchange endpoint with
        # the real client ID and secret, but a fake auth code to exchange. Gitlab's implementation will
        # return `invalid_client` as the `error` if the client ID or secret is invalid; otherwise, it
        # will return another error.
        url = self.token_endpoint().to_url()
        redirect_uri = self.get_redirect_uri(url_scheme_and_hostname, redirect_suffix="trigger")
        data = {
            "code": "fakecode",
            "client_id": self.client_id(),
            "client_secret": self.client_secret(),
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        # We validate by checking the error code we receive from this call.
        result = http_client.post(url, data=data, timeout=5)
        value = result.json()
        if not value:
            return False

        return value.get("error", "") != "invalid_client"

    def get_public_config(self):
        return {
            "CLIENT_ID": self.client_id(),
            "AUTHORIZE_ENDPOINT": self.authorize_endpoint().to_url(),
            "GITLAB_ENDPOINT": self._endpoint(),
        }
