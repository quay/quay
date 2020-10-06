from oauth.loginmanager import OAuthLoginManager
from oauth.services.github import GithubOAuthService
from oauth.services.google import GoogleOAuthService
from oauth.services.openshift import OpenshiftOAuthService
from oauth.oidc import OIDCLoginService


def test_login_manager_github():
    config = {
        "FEATURE_GITHUB_LOGIN": True,
        "GITHUB_LOGIN_CONFIG": {},
    }

    loginmanager = OAuthLoginManager(config)
    assert len(loginmanager.services) == 1
    assert isinstance(loginmanager.services[0], GithubOAuthService)


def test_github_disabled():
    config = {
        "GITHUB_LOGIN_CONFIG": {},
    }

    loginmanager = OAuthLoginManager(config)
    assert len(loginmanager.services) == 0


def test_login_manager_google():
    config = {
        "FEATURE_GOOGLE_LOGIN": True,
        "GOOGLE_LOGIN_CONFIG": {},
    }

    loginmanager = OAuthLoginManager(config)
    assert len(loginmanager.services) == 1
    assert isinstance(loginmanager.services[0], GoogleOAuthService)


def test_google_disabled():
    config = {
        "GOOGLE_LOGIN_CONFIG": {},
    }

    loginmanager = OAuthLoginManager(config)
    assert len(loginmanager.services) == 0


def test_oidc():
    config = {
        "SOMECOOL_LOGIN_CONFIG": {},
        "HTTPCLIENT": None,
    }

    loginmanager = OAuthLoginManager(config)
    assert len(loginmanager.services) == 1
    assert isinstance(loginmanager.services[0], OIDCLoginService)


def test_multiple_oidc():
    config = {
        "SOMECOOL_LOGIN_CONFIG": {},
        "ANOTHER_LOGIN_CONFIG": {},
        "HTTPCLIENT": None,
    }

    loginmanager = OAuthLoginManager(config)
    assert len(loginmanager.services) == 2
    assert isinstance(loginmanager.services[0], OIDCLoginService)
    assert isinstance(loginmanager.services[1], OIDCLoginService)


def test_login_manager_openshift():
    config = {
        "FEATURE_OPENSHIFT_LOGIN": True,
        "OPENSHIFT_LOGIN_CONFIG": {},
    }

    loginmanager = OAuthLoginManager(config)
    assert len(loginmanager.services) == 1
    assert isinstance(loginmanager.services[0], OpenshiftOAuthService)
