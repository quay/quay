import logging

from oauth.base import OAuthEndpoint
from oauth.login import OAuthLoginService, OAuthLoginException
from util import slash_join

logger = logging.getLogger(__name__)


class GithubOAuthService(OAuthLoginService):
    def __init__(self, config, key_name):
        super(GithubOAuthService, self).__init__(config, key_name)

    def login_enabled(self, config):
        return config.get("FEATURE_GITHUB_LOGIN", False)

    def service_id(self):
        return "github"

    def service_name(self):
        if self.is_enterprise():
            return "GitHub Enterprise"

        return "GitHub"

    def get_icon(self):
        return "fa-github"

    def get_login_scopes(self):
        if self.config.get("ORG_RESTRICT"):
            return ["user:email", "read:org"]

        return ["user:email"]

    def allowed_organizations(self):
        if not self.config.get("ORG_RESTRICT", False):
            return None

        allowed = self.config.get("ALLOWED_ORGANIZATIONS", None)
        if allowed is None:
            return None

        return [org.lower() for org in allowed]

    def get_public_url(self, suffix):
        return slash_join(self._endpoint(), suffix)

    def _endpoint(self):
        return self.config.get("GITHUB_ENDPOINT", "https://github.com")

    def is_enterprise(self):
        return self._api_endpoint().find(".github.com") < 0

    def authorize_endpoint(self):
        return OAuthEndpoint(slash_join(self._endpoint(), "/login/oauth/authorize"))

    def token_endpoint(self):
        return OAuthEndpoint(slash_join(self._endpoint(), "/login/oauth/access_token"))

    def user_endpoint(self):
        return OAuthEndpoint(slash_join(self._api_endpoint(), "user"))

    def _api_endpoint(self):
        return self.config.get("API_ENDPOINT", slash_join(self._endpoint(), "/api/v3/"))

    def api_endpoint(self):
        endpoint = self._api_endpoint()
        if endpoint.endswith("/"):
            return endpoint[0:-1]

        return endpoint

    def email_endpoint(self):
        return slash_join(self._api_endpoint(), "user/emails")

    def orgs_endpoint(self):
        return slash_join(self._api_endpoint(), "user/orgs")

    def validate_client_id_and_secret(self, http_client, url_scheme_and_hostname):
        # First: Verify that the github endpoint is actually Github by checking for the
        # X-GitHub-Request-Id here.
        api_endpoint = self._api_endpoint()
        result = http_client.get(
            api_endpoint, auth=(self.client_id(), self.client_secret()), timeout=5
        )
        if not "X-GitHub-Request-Id" in result.headers:
            raise Exception("Endpoint is not a Github (Enterprise) installation")

        # Next: Verify the client ID and secret.
        # Note: The following code is a hack until such time as Github officially adds an API endpoint
        # for verifying a {client_id, client_secret} pair. This workaround was given to us
        # *by a Github Engineer* (Jan 8, 2015).
        #
        # TODO: Replace with the real API call once added.
        #
        # Hitting the endpoint applications/{client_id}/tokens/foo will result in the following
        # behavior IF the client_id is given as the HTTP username and the client_secret as the HTTP
        # password:
        #   - If the {client_id, client_secret} pair is invalid in some way, we get a 401 error.
        #   - If the pair is valid, then we get a 404 because the 'foo' token does not exists.
        validate_endpoint = slash_join(
            api_endpoint, "applications/%s/tokens/foo" % self.client_id()
        )
        result = http_client.get(
            validate_endpoint, auth=(self.client_id(), self.client_secret()), timeout=5
        )
        return result.status_code == 404

    def validate_organization(self, organization_id, http_client):
        org_endpoint = slash_join(self._api_endpoint(), "orgs/%s" % organization_id.lower())

        result = http_client.get(
            org_endpoint, headers={"Accept": "application/vnd.github.moondragon+json"}, timeout=5
        )

        return result.status_code == 200

    def get_public_config(self):
        return {
            "CLIENT_ID": self.client_id(),
            "AUTHORIZE_ENDPOINT": self.authorize_endpoint().to_url(),
            "GITHUB_ENDPOINT": self._endpoint(),
            "ORG_RESTRICT": self.config.get("ORG_RESTRICT", False),
        }

    def get_login_service_id(self, user_info):
        return user_info["id"]

    def get_login_service_username(self, user_info):
        return user_info["login"]

    def get_verified_user_email(self, app_config, http_client, token, user_info):
        v3_media_type = {
            "Accept": "application/vnd.github.v3",
            "Authorization": "token %s" % token,
        }

        # Find the e-mail address for the user: we will accept any email, but we prefer the primary
        get_email = http_client.get(self.email_endpoint(), headers=v3_media_type)
        if get_email.status_code // 100 != 2:
            raise OAuthLoginException(
                "Got non-2XX status code for emails endpoint: %s" % get_email.status_code
            )

        verified_emails = [email for email in get_email.json() if email["verified"]]
        primary_emails = [email for email in get_email.json() if email["primary"]]

        # Special case: We don't care about whether an e-mail address is "verified" under GHE.
        if self.is_enterprise() and not verified_emails:
            verified_emails = primary_emails

        allowed_emails = primary_emails or verified_emails or []
        return allowed_emails[0]["email"] if len(allowed_emails) > 0 else None

    def service_verify_user_info_for_login(self, app_config, http_client, token, user_info):
        # Retrieve the user's organizations (if organization filtering is turned on)
        if self.allowed_organizations() is None:
            return

        moondragon_media_type = {
            "Accept": "application/vnd.github.moondragon+json",
            "Authorization": "token %s" % token,
        }

        get_orgs = http_client.get(self.orgs_endpoint(), headers=moondragon_media_type)

        if get_orgs.status_code // 100 != 2:
            logger.debug("get_orgs response: %s", get_orgs.json())
            raise OAuthLoginException(
                "Got non-2XX response for org lookup: %s" % get_orgs.status_code
            )

        organizations = set([org.get("login").lower() for org in get_orgs.json()])
        matching_organizations = organizations & set(self.allowed_organizations())
        if not matching_organizations:
            logger.debug(
                "Found organizations %s, but expected one of %s",
                organizations,
                self.allowed_organizations(),
            )
            err = """You are not a member of an allowed GitHub organization.
               Please contact your system administrator if you believe this is in error."""
            raise OAuthLoginException(err)
