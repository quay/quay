from oauth.base import OAuthEndpoint
from oauth.login import OAuthLoginService


def _get_email_username(email_address):
    username = email_address
    at = username.find("@")
    if at > 0:
        username = username[0:at]

    return username


class GoogleOAuthService(OAuthLoginService):
    def __init__(self, config, key_name):
        super(GoogleOAuthService, self).__init__(config, key_name)

    def login_enabled(self, config):
        return config.get("FEATURE_GOOGLE_LOGIN", False)

    def service_id(self):
        return "google"

    def service_name(self):
        return "Google"

    def get_icon(self):
        return "fa-google"

    def get_login_scopes(self):
        return ["openid", "email"]

    def authorize_endpoint(self):
        return OAuthEndpoint(
            "https://accounts.google.com/o/oauth2/auth", params=dict(response_type="code")
        )

    def token_endpoint(self):
        return OAuthEndpoint("https://accounts.google.com/o/oauth2/token")

    def user_endpoint(self):
        return OAuthEndpoint("https://www.googleapis.com/oauth2/v1/userinfo")

    def requires_form_encoding(self):
        return True

    def validate_client_id_and_secret(self, http_client, url_scheme_and_hostname):
        # To verify the Google client ID and secret, we hit the
        # https://www.googleapis.com/oauth2/v3/token endpoint with an invalid request. If the client
        # ID or secret are invalid, we get returned a 403 Unauthorized. Otherwise, we get returned
        # another response code.
        url = "https://www.googleapis.com/oauth2/v3/token"
        data = {
            "code": "fakecode",
            "client_id": self.client_id(),
            "client_secret": self.client_secret(),
            "grant_type": "authorization_code",
            "redirect_uri": "http://example.com",
        }

        result = http_client.post(url, data=data, timeout=5)
        return result.status_code != 401

    def get_public_config(self):
        return {
            "CLIENT_ID": self.client_id(),
            "AUTHORIZE_ENDPOINT": self.authorize_endpoint().to_url(),
        }

    def get_login_service_id(self, user_info):
        return user_info["id"]

    def get_login_service_username(self, user_info):
        return _get_email_username(user_info["email"])

    def get_verified_user_email(self, app_config, http_client, token, user_info):
        if not user_info.get("verified_email", False):
            return None

        return user_info["email"]

    def service_verify_user_info_for_login(self, app_config, http_client, token, user_info):
        # Nothing to do.
        pass
