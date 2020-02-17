import pytest

from oauth.services.github import GithubOAuthService


@pytest.mark.parametrize(
    "trigger_config, domain, api_endpoint, is_enterprise",
    [
        (
            {
                "CLIENT_ID": "someclientid",
                "CLIENT_SECRET": "someclientsecret",
                "API_ENDPOINT": "https://api.github.com/v3",
            },
            "https://github.com",
            "https://api.github.com/v3",
            False,
        ),
        (
            {
                "GITHUB_ENDPOINT": "https://github.somedomain.com/",
                "CLIENT_ID": "someclientid",
                "CLIENT_SECRET": "someclientsecret",
            },
            "https://github.somedomain.com",
            "https://github.somedomain.com/api/v3",
            True,
        ),
        (
            {
                "GITHUB_ENDPOINT": "https://github.somedomain.com/",
                "API_ENDPOINT": "http://somedomain.com/api/",
                "CLIENT_ID": "someclientid",
                "CLIENT_SECRET": "someclientsecret",
            },
            "https://github.somedomain.com",
            "http://somedomain.com/api",
            True,
        ),
    ],
)
def test_basic_enterprise_config(trigger_config, domain, api_endpoint, is_enterprise):
    config = {"GITHUB_TRIGGER_CONFIG": trigger_config}

    github_trigger = GithubOAuthService(config, "GITHUB_TRIGGER_CONFIG")
    assert github_trigger.is_enterprise() == is_enterprise

    assert github_trigger.authorize_endpoint().to_url() == "%s/login/oauth/authorize" % domain

    assert github_trigger.token_endpoint().to_url() == "%s/login/oauth/access_token" % domain

    assert github_trigger.api_endpoint() == api_endpoint
    assert github_trigger.user_endpoint().to_url() == "%s/user" % api_endpoint
    assert github_trigger.email_endpoint() == "%s/user/emails" % api_endpoint
    assert github_trigger.orgs_endpoint() == "%s/user/orgs" % api_endpoint
