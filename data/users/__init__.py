import itertools
import json
import logging
import uuid
from typing import Union

import features
from data import model
from data.users.apptoken import AppTokenInternalAuth
from data.users.database import DatabaseUsers
from data.users.externaljwt import ExternalJWTAuthN
from data.users.externalldap import LDAPUsers
from data.users.externaloidc import OIDCUsers
from data.users.federated import FederatedUsers
from data.users.keystone import get_keystone_users
from oauth.oidc import OIDCLoginService
from util.config.superusermanager import ConfigUserManager
from util.security.aes import AESCipher
from util.security.secret import convert_secret_key

logger = logging.getLogger(__name__)


def get_federated_service_name(authentication_type):
    if authentication_type == "LDAP":
        return "ldap"

    if authentication_type == "JWT":
        return "jwtauthn"

    if authentication_type == "Keystone":
        return "keystone"

    if authentication_type == "AppToken":
        return None

    if authentication_type == "Database":
        return None

    if authentication_type == "OIDC":
        return "oidc"

    raise Exception("Unknown auth type: %s" % authentication_type)


LDAP_CERT_FILENAME = "ldap.crt"


def get_users_handler(config, _, override_config_dir, oauth_login):
    """
    Returns a users handler for the authentication configured in the given config object.
    """
    authentication_type = config.get("AUTHENTICATION_TYPE", "Database")

    if authentication_type == "Database":
        return DatabaseUsers()

    if authentication_type == "LDAP":
        ldap_uri = config.get("LDAP_URI", "ldap://localhost")
        base_dn = config.get("LDAP_BASE_DN")
        admin_dn = config.get("LDAP_ADMIN_DN")
        admin_passwd = config.get("LDAP_ADMIN_PASSWD")
        user_rdn = config.get("LDAP_USER_RDN", [])
        uid_attr = config.get("LDAP_UID_ATTR", "uid")
        email_attr = config.get("LDAP_EMAIL_ATTR", "mail")
        memberof_attr = config.get("LDAP_MEMBEROF_ATTR", "memberOf")
        secondary_user_rdns = config.get("LDAP_SECONDARY_USER_RDNS", [])
        timeout = config.get("LDAP_TIMEOUT")
        network_timeout = config.get("LDAP_NETWORK_TIMEOUT")
        ldap_user_filter = config.get("LDAP_USER_FILTER", None)
        ldap_superuser_filter = config.get("LDAP_SUPERUSER_FILTER", None)
        ldap_global_readonly_superuser_filter = config.get(
            "LDAP_GLOBAL_READONLY_SUPERUSER_FILTER", None
        )
        ldap_restricted_user_filter = config.get("LDAP_RESTRICTED_USER_FILTER", None)
        ldap_referrals = int(config.get("LDAP_FOLLOW_REFERRALS", True))

        allow_tls_fallback = config.get("LDAP_ALLOW_INSECURE_FALLBACK", False)
        return LDAPUsers(
            ldap_uri,
            base_dn,
            admin_dn,
            admin_passwd,
            user_rdn,
            uid_attr,
            email_attr,
            memberof_attr,
            allow_tls_fallback,
            secondary_user_rdns=secondary_user_rdns,
            requires_email=features.MAILING,
            timeout=timeout,
            network_timeout=network_timeout,
            ldap_user_filter=ldap_user_filter,
            ldap_superuser_filter=ldap_superuser_filter,
            ldap_global_readonly_superuser_filter=ldap_global_readonly_superuser_filter,
            ldap_restricted_user_filter=ldap_restricted_user_filter,
            ldap_referrals=ldap_referrals,
        )

    if authentication_type == "JWT":
        verify_url = config.get("JWT_VERIFY_ENDPOINT")
        issuer = config.get("JWT_AUTH_ISSUER")
        max_fresh_s = config.get("JWT_AUTH_MAX_FRESH_S", 300)

        query_url = config.get("JWT_QUERY_ENDPOINT", None)
        getuser_url = config.get("JWT_GETUSER_ENDPOINT", None)

        return ExternalJWTAuthN(
            verify_url,
            query_url,
            getuser_url,
            issuer,
            override_config_dir,
            config["HTTPCLIENT"],
            max_fresh_s,
            requires_email=features.MAILING,
        )

    if authentication_type == "Keystone":
        auth_url = config.get("KEYSTONE_AUTH_URL")
        auth_version = int(config.get("KEYSTONE_AUTH_VERSION", 2))
        timeout = config.get("KEYSTONE_AUTH_TIMEOUT")
        keystone_admin_username = config.get("KEYSTONE_ADMIN_USERNAME")
        keystone_admin_password = config.get("KEYSTONE_ADMIN_PASSWORD")
        keystone_admin_tenant = config.get("KEYSTONE_ADMIN_TENANT")
        return get_keystone_users(
            auth_version,
            auth_url,
            keystone_admin_username,
            keystone_admin_password,
            keystone_admin_tenant,
            timeout,
            requires_email=features.MAILING,
        )

    if authentication_type == "AppToken":
        if features.DIRECT_LOGIN:
            raise Exception("Direct login feature must be disabled to use AppToken internal auth")

        if not features.APP_SPECIFIC_TOKENS:
            raise Exception(
                "AppToken internal auth requires app specific token support to be enabled"
            )

        return AppTokenInternalAuth()

    if authentication_type == "OIDC" and oauth_login:
        for service in oauth_login.services:
            if isinstance(service, OIDCLoginService):
                config = service.config
                client_id = config.get("CLIENT_ID", None)
                client_secret = config.get("CLIENT_SECRET", None)
                oidc_server = config.get("OIDC_SERVER", None)
                service_name = config.get("SERVICE_NAME", None)
                login_scopes = config.get("LOGIN_SCOPES", None)
                preferred_group_claim_name = config.get("PREFERRED_GROUP_CLAIM_NAME", None)

                return OIDCUsers(
                    client_id,
                    client_secret,
                    oidc_server,
                    service_name,
                    login_scopes,
                    preferred_group_claim_name,
                )

    raise RuntimeError("Unknown authentication type: %s" % authentication_type)


class UserAuthentication(object):
    def __init__(self, app=None, config_provider=None, override_config_dir=None, oauth_login=None):
        self.secret_key = None
        self.app = app
        if app is not None:
            self.state = self.init_app(app, config_provider, override_config_dir, oauth_login)
        else:
            self.state = None

    def init_app(self, app, config_provider, override_config_dir, oauth_login):
        self.secret_key = convert_secret_key(app.config["SECRET_KEY"])
        users = get_users_handler(app.config, config_provider, override_config_dir, oauth_login)

        # register extension with app
        app.extensions = getattr(app, "extensions", {})
        app.extensions["authentication"] = users

        return users

    def encrypt_user_password(self, password):
        """
        Returns an encrypted version of the user's password.
        """
        data = {"password": password}

        message = json.dumps(data).encode("utf-8")
        cipher = AESCipher(self.secret_key)
        return cipher.encrypt(message)

    def _decrypt_user_password(self, encrypted):
        """
        Attempts to decrypt the given password and returns it.
        """
        cipher = AESCipher(self.secret_key)

        try:
            message = cipher.decrypt(encrypted)
        except ValueError:
            return None
        except TypeError:
            return None

        try:
            data = json.loads(message.decode("utf-8"))
        except ValueError:
            return None

        return data.get("password", encrypted)

    def ping(self):
        """
        Returns whether the authentication engine is reachable and working.
        """
        return self.state.ping()

    @property
    def federated_service(self):
        """
        Returns the name of the federated service for the auth system.

        If none, should return None.
        """
        return self.state.federated_service

    @property
    def requires_distinct_cli_password(self):
        """
        Returns whether this auth system requires a distinct CLI password to be created, in-system,
        before the CLI can be used.
        """
        return self.state.requires_distinct_cli_password

    @property
    def supports_encrypted_credentials(self):
        """
        Returns whether this auth system supports using encrypted credentials.
        """
        return self.state.supports_encrypted_credentials

    def has_password_set(self, username):
        """
        Returns whether the user has a password set in the auth system.
        """
        return self.state.has_password_set(username)

    @property
    def supports_fresh_login(self):
        """
        Returns whether this auth system supports the fresh login check.
        """
        return self.state.supports_fresh_login

    def query_users(self, query, limit=20):
        """
        Performs a lookup against the user system for the specified query. The returned tuple will
        be of the form (results, federated_login_id, err_msg). If the method is unsupported, the
        results portion of the tuple will be None instead of empty list.

        Note that this method can and will return results for users not yet found within the
        database; it is the responsibility of the caller to call link_user if they need the
        database row for the user system record.

        Results will be in the form of objects's with username and email fields.
        """
        return self.state.query_users(query, limit)

    def link_user(self, username_or_email):
        """
        Returns a tuple containing the database user record linked to the given username/email and
        any error that occurred when trying to link the user.
        """
        return self.state.link_user(username_or_email)

    def get_and_link_federated_user_info(self, user_info, internal_create=False):
        """
        Returns a tuple containing the database user record linked to the given UserInformation pair
        and any error that occurred when trying to link the user.

        If `internal_create` is True, the caller is an internal user creation process (such as team
        syncing), and the "can a user be created" check will be bypassed.
        """
        return self.state.get_and_link_federated_user_info(
            user_info, internal_create=internal_create
        )

    def confirm_existing_user(self, username, password):
        """
        Verifies that the given password matches to the given DB username.

        Unlike verify_credentials, this call first translates the DB user via the FederatedLogin
        table (where applicable).
        """
        return self.state.confirm_existing_user(username, password)

    def verify_credentials(self, username_or_email, password):
        """
        Verifies that the given username and password credentials are valid.
        """
        return self.state.verify_credentials(username_or_email, password)

    def check_group_lookup_args(self, group_lookup_args):
        """
        Verifies that the given group lookup args point to a valid group.

        Returns a tuple consisting of a boolean status and an error message (if any).
        """
        return self.state.check_group_lookup_args(group_lookup_args)

    def service_metadata(self):
        """
        Returns a dictionary of extra metadata to present to *superusers* about this auth engine.

        For example, LDAP returns the base DN so we can display to the user during sync setup.
        """
        return self.state.service_metadata()

    def iterate_group_members(self, group_lookup_args, page_size=None, disable_pagination=False):
        """
        Returns a tuple of an iterator over all the members of the group matching the given lookup
        args dictionary, or the error that occurred if the initial call failed or is unsupported.

        The format of the lookup args dictionary is specific to the implementation. Each result in
        the iterator is a tuple of (UserInformation, error_message), and only one will be not-None.
        """
        return self.state.iterate_group_members(
            group_lookup_args, page_size=page_size, disable_pagination=disable_pagination
        )

    def verify_and_link_user(self, username_or_email, password, basic_auth=False):
        """
        Verifies that the given username and password credentials are valid and, if so, creates or
        links the database user to the federated identity.
        """
        # First try to decode the password as a signed token.
        if basic_auth:
            decrypted = self._decrypt_user_password(password)
            if decrypted is None:
                # This is a normal password.
                if features.REQUIRE_ENCRYPTED_BASIC_AUTH:
                    msg = (
                        "Client login with unencrypted passwords is disabled. Please generate an "
                        + "encrypted password in the user admin panel for use here."
                    )
                    return (None, msg)
            else:
                password = decrypted

        (result, err_msg) = self.state.verify_and_link_user(username_or_email, password)
        if not result:
            return (result, err_msg)

        if not result.enabled:
            return (None, "This user has been disabled. Please contact your administrator.")

        return (result, err_msg)

    def is_superuser(self, username):
        return self.state.is_superuser(username)

    def is_global_readonly_superuser(self, username):
        return self.state.is_global_readonly_superuser(username)

    def has_superusers(self):
        return self.state.has_superusers()

    def is_restricted_user(self, username):
        return self.state.is_restricted_user(username)

    def has_restricted_users(self):
        return self.state.has_restricted_users()

    def __getattr__(self, name):
        return getattr(self.state, name, None)


class UserManager(object):
    def __init__(self, app, authentication: UserAuthentication):
        self.authentication = authentication
        self.state = self.init_app(app, authentication)

    def init_app(self, app, authentication: UserAuthentication):
        manager = None  # type: Union[FederatedUserManager, ConfigUserManager, None]
        if authentication.federated_service:
            manager = FederatedUserManager(app, authentication)
        else:
            manager = ConfigUserManager(app)

        return manager

    def __getattr__(self, name):
        return getattr(self.state, name, None)

    def is_restricted_user(self, username):
        if not features.RESTRICTED_USERS:
            return False

        return self.state.is_restricted_user(username)

    def is_superuser(self, username):
        if not features.SUPER_USERS:
            return False

        return self.state.is_superuser(username)


class FederatedUserManager(ConfigUserManager):
    """
    Helper class to access superusers defined in the backed federated provider.
    Falls back to the in-memory helper if not available in the federated service.
    """

    def __init__(self, app, authentication: UserAuthentication):
        self.federated_users = authentication
        super().__init__(app)

    def is_superuser(self, username: str) -> bool:
        """
        Returns if the given username represents a super user.
        """
        return self.federated_users.is_superuser(username) or super().is_superuser(username)

    def has_superusers(self) -> bool:
        """
        Returns whether there are any superusers defined.
        """
        return self.federated_users.has_superusers() or super().has_superusers()

    def is_restricted_user(self, username: str, include_robots: bool = True) -> bool:
        """
        Returns if the given username represents a restricted user.
        """
        if include_robots:
            username = username.split("+", 1)[0]

        if super().restricted_whitelist_is_set() and not super().is_restricted_user(username):
            return False

        return self.federated_users.is_restricted_user(username) or super().is_restricted_user(
            username
        )

    def has_restricted_users(self) -> bool:
        return self.federated_users.has_restricted_users() or super().has_restricted_users()

    def is_global_readonly_superuser(self, username: str) -> bool:
        return self.federated_users.is_global_readonly_superuser(
            username
        ) or super().is_global_readonly_superuser(username)
