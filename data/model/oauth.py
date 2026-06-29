import json
import logging
import posixpath
from datetime import datetime, timedelta
from math import isfinite
from urllib.parse import unquote, urlparse

from flask import url_for
from peewee import JOIN

from auth import scopes
from data.database import (
    OAuthAccessToken,
    OAuthApplication,
    OauthAssignedToken,
    OAuthAuthorizationCode,
    User,
    compute_advisory_lock_id,
    db_advisory_xact_lock,
    db_for_update,
    random_string_generator,
)
from data.fields import Credential, DecryptedValue
from data.model import config, db_transaction, notification, user
from data.model.modelutil import paginate
from data.model.organization import is_org_admin
from oauth import utils
from oauth.provider import AuthorizationProvider
from util import get_app_url

logger = logging.getLogger(__name__)

ACCESS_TOKEN_PREFIX_LENGTH = 20
ACCESS_TOKEN_MINIMUM_CODE_LENGTH = 20
AUTHORIZATION_CODE_PREFIX_LENGTH = 20
MAX_TOKENS_PER_APPLICATION = 1000
DEFAULT_TOKEN_EXPIRATION_SECONDS = int(60 * 60 * 24 * 365.25 * 10)  # 10 years
BOOTSTRAP_APP_NAME = "__quay_bootstrap_app"
BOOTSTRAP_APP_DESCRIPTION = "Auto-created by bootstrap token provisioning"
BOOTSTRAP_TOKEN_LOCK_ID = compute_advisory_lock_id("bootstrap_token", 0)


class TokenLimitExceeded(Exception):
    """Raised when an OAuth application has reached its active token limit."""


def get_bootstrap_app_name(app_config=None):
    """Return the configured bootstrap OAuth application name."""
    if app_config is None:
        app_config = config.app_config or {}

    return app_config.get("BOOTSTRAP_APP_NAME", BOOTSTRAP_APP_NAME)


def get_bootstrap_app_names(app_config=None):
    """Return reserved bootstrap OAuth application names for current config."""
    return {BOOTSTRAP_APP_NAME, get_bootstrap_app_name(app_config)}


def is_bootstrap_app_name(name, app_config=None):
    """Return whether name is reserved for bootstrap OAuth applications."""
    return name in get_bootstrap_app_names(app_config)


def normalize_scope(scope_string):
    """Normalize a comma- or space-separated scope string to space-separated, deduplicated."""
    normalized = scope_string.replace(",", " ")
    return " ".join(dict.fromkeys(normalized.split()))


def validate_expiration(value):
    """
    Validate and return an integer expiration in seconds.

    Raises ValueError if the value is not a finite positive number.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("'expiration' must be a positive number of seconds")

    if isinstance(value, float) and not isfinite(value):
        raise ValueError("'expiration' must be a finite number of seconds")

    if value <= 0:
        raise ValueError("'expiration' must be a positive number of seconds")

    return int(value)


class DatabaseAuthorizationProvider(AuthorizationProvider):
    def get_authorized_user(self):
        raise NotImplementedError("Subclasses must fill in the ability to get the authorized_user.")

    def _generate_data_string(self):
        return json.dumps({"username": self.get_authorized_user().username})

    @property
    def token_expires_in(self):
        """
        Property method to get the token expiration time in seconds.
        """
        return DEFAULT_TOKEN_EXPIRATION_SECONDS

    def validate_client_id(self, client_id):
        return self.get_application_for_client_id(client_id) is not None

    def get_application_for_client_id(self, client_id):
        try:
            return OAuthApplication.get(client_id=client_id)
        except OAuthApplication.DoesNotExist:
            return None

    def validate_client_secret(self, client_id, client_secret):
        try:
            application = OAuthApplication.get(client_id=client_id)
            assert application.secure_client_secret is not None
            return application.secure_client_secret.matches(client_secret)
        except OAuthApplication.DoesNotExist:
            return False

    def validate_redirect_uri(self, client_id, redirect_uri):
        internal_redirect_url = "%s%s" % (
            get_app_url(config.app_config),
            url_for("web.oauth_local_handler"),
        )

        # Exact match for internal redirect
        if redirect_uri == internal_redirect_url:
            return True

        try:
            oauth_app = OAuthApplication.get(client_id=client_id)

            if not oauth_app.redirect_uri or not redirect_uri:
                return False

            # Parse URLs for secure validation
            configured = urlparse(oauth_app.redirect_uri)
            provided = urlparse(redirect_uri)

            # Scheme must match exactly (prevent protocol downgrade)
            if configured.scheme != provided.scheme:
                return False

            # Netloc must match exactly (prevent subdomain takeover)
            if configured.netloc != provided.netloc:
                return False

            # Block username/password in URI (security risk)
            if provided.username or provided.password:
                return False

            # Decode path to catch encoded traversal attacks (e.g., %2e%2e)
            provided_path_decoded = unquote(provided.path)

            # Block path traversal attempts (both encoded and literal)
            if ".." in provided_path_decoded:
                return False

            # Block @ in path (can be used for credential injection)
            if "@" in provided.path:
                return False

            # Strict validation: path prefix must match
            if not provided.path.startswith(configured.path):
                return False

            # Block percent-encoding after prefix (prevents double-encoding attacks)
            path_after_prefix = provided.path[len(configured.path) :]
            if "%" in path_after_prefix:
                return False

            return True
        except OAuthApplication.DoesNotExist:
            return False

    def validate_scope(self, client_id, scopes_string):
        return scopes.validate_scope_string(scopes_string)

    def validate_access(self):
        return self.get_authorized_user() is not None

    def load_authorized_scope_string(self, client_id, username):
        found = (
            OAuthAccessToken.select()
            .join(OAuthApplication)
            .switch(OAuthAccessToken)
            .join(User, on=(OAuthAccessToken.authorized_user == User.id))
            .where(
                OAuthApplication.client_id == client_id,
                User.username == username,
                OAuthAccessToken.expires_at > datetime.utcnow(),
            )
        )
        found = list(found)
        logger.debug("Found %s matching tokens.", len(found))
        long_scope_string = ",".join([token.scope for token in found])
        logger.debug("Computed long scope string: %s", long_scope_string)
        return long_scope_string

    def validate_has_scopes(self, client_id, username, scope):
        long_scope_string = self.load_authorized_scope_string(client_id, username)

        # Make sure the token contains the given scopes (at least).
        return scopes.is_subset_string(long_scope_string, scope)

    def from_authorization_code(self, client_id, code, scope):
        code_name = code[:AUTHORIZATION_CODE_PREFIX_LENGTH]
        code_credential = code[AUTHORIZATION_CODE_PREFIX_LENGTH:]

        try:
            found = (
                OAuthAuthorizationCode.select()
                .join(OAuthApplication)
                .where(
                    OAuthApplication.client_id == client_id,
                    OAuthAuthorizationCode.code_name == code_name,
                    OAuthAuthorizationCode.scope == scope,
                )
                .get()
            )
            if not found.code_credential.matches(code_credential):
                return None

            logger.debug("Returning data: %s", found.data)
            return found.data
        except OAuthAuthorizationCode.DoesNotExist:
            return None

    def persist_authorization_code(self, client_id, code, scope):
        oauth_app = OAuthApplication.get(client_id=client_id)
        data = self._generate_data_string()

        assert len(code) >= (AUTHORIZATION_CODE_PREFIX_LENGTH * 2)
        code_name = code[:AUTHORIZATION_CODE_PREFIX_LENGTH]
        code_credential = code[AUTHORIZATION_CODE_PREFIX_LENGTH:]

        OAuthAuthorizationCode.create(
            application=oauth_app,
            scope=scope,
            code_name=code_name,
            code_credential=Credential.from_string(code_credential),
            data=data,
        )

    def persist_token_information(
        self, client_id, scope, access_token, token_type, expires_in, refresh_token, data
    ):
        assert not refresh_token
        found = user.get_user(json.loads(data)["username"])
        if not found:
            raise RuntimeError("Username must be in the data field")

        token_name = access_token[:ACCESS_TOKEN_PREFIX_LENGTH]
        token_code = access_token[ACCESS_TOKEN_PREFIX_LENGTH:]

        assert token_name
        assert token_code
        assert len(token_name) == ACCESS_TOKEN_PREFIX_LENGTH
        assert len(token_code) >= ACCESS_TOKEN_MINIMUM_CODE_LENGTH

        oauth_app = OAuthApplication.get(client_id=client_id)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        OAuthAccessToken.create(
            application=oauth_app,
            authorized_user=found,
            scope=scope,
            token_name=token_name,
            token_code=Credential.from_string(token_code),
            access_token="",
            token_type=token_type,
            expires_at=expires_at,
            data=data,
        )

    def get_auth_denied_response(self, response_type, client_id, redirect_uri, **params):
        # Ensure proper response_type
        if response_type != "token":
            err = "unsupported_response_type"
            return self._make_redirect_error_response(redirect_uri, err)

        # Check redirect URI
        is_valid_redirect_uri = self.validate_redirect_uri(client_id, redirect_uri)
        if not is_valid_redirect_uri:
            return self._invalid_redirect_uri_response()

        return self._make_redirect_error_response(redirect_uri, "authorization_denied")

    def get_token_response(
        self, response_type, client_id, redirect_uri, assignment_uuid=None, **params
    ):
        # Ensure proper response_type
        if response_type != "token":
            err = "unsupported_response_type"
            return self._make_redirect_error_response(redirect_uri, err)

        # Check for a valid client ID.
        oauth_application = self.get_application_for_client_id(client_id)

        if oauth_application is None or not self.is_org_admin_or_has_token_assignment(
            oauth_application.organization, assignment_uuid
        ):
            err = "unauthorized_client"
            return self._make_redirect_error_response(redirect_uri, err)

        # Check for a valid redirect URI.
        is_valid_redirect_uri = self.validate_redirect_uri(client_id, redirect_uri)
        if not is_valid_redirect_uri:
            return self._invalid_redirect_uri_response()

        # Check conditions
        is_valid_access = self.validate_access()
        scope = params.get("scope", "")
        are_valid_scopes = self.validate_scope(client_id, scope)

        # Return proper error responses on invalid conditions
        if not is_valid_access:
            err = "access_denied"
            return self._make_redirect_error_response(redirect_uri, err)

        if not are_valid_scopes:
            err = "invalid_scope"
            return self._make_redirect_error_response(redirect_uri, err)

        # Make sure we have enough random data in the token to have a public
        # prefix and a private encrypted suffix.
        access_token = str(self.generate_access_token())
        assert len(access_token) - ACCESS_TOKEN_PREFIX_LENGTH >= 20

        token_type = self.token_type
        expires_in = self.token_expires_in

        data = self._generate_data_string()
        self.persist_token_information(
            client_id=client_id,
            scope=scope,
            access_token=access_token,
            token_type=token_type,
            expires_in=expires_in,
            refresh_token=None,
            data=data,
        )

        # check for assignment_id and delete it if it exists
        if assignment_uuid is not None:
            user_obj = self.get_authorized_user()
            assign = get_token_assignment_for_client_id(assignment_uuid, user_obj, client_id)
            if assign is not None:
                assign.delete_instance()

        url = utils.build_url(redirect_uri, params)
        url += "#access_token=%s&token_type=%s&expires_in=%s" % (
            access_token,
            token_type,
            expires_in,
        )

        return self._make_response(headers={"Location": url}, status_code=302)

    def generate_refresh_token(self):
        return None

    def from_refresh_token(self, client_id, refresh_token, scope):
        raise NotImplementedError()

    def discard_authorization_code(self, client_id, code):
        code_name = code[:AUTHORIZATION_CODE_PREFIX_LENGTH]
        try:
            found = (
                OAuthAuthorizationCode.select()
                .join(OAuthApplication)
                .where(
                    OAuthApplication.client_id == client_id,
                    OAuthAuthorizationCode.code_name == code_name,
                )
                .get()
            )
            found.delete_instance()
            return
        except OAuthAuthorizationCode.DoesNotExist:
            pass

    def discard_refresh_token(self, client_id, refresh_token):
        raise NotImplementedError()

    def is_org_admin_or_has_token_assignment(self, organization, assignment_uuid):
        return (
            is_org_admin(self.get_authorized_user(), organization)
            or get_token_assignment(assignment_uuid, self.get_authorized_user(), organization)
            is not None
        )


def get_or_create_bootstrap_application(name, org):
    """Return the reserved bootstrap app for org, or create it if missing."""
    try:
        return (
            OAuthApplication.select()
            .where(
                OAuthApplication.name == name,
                OAuthApplication.organization == org,
            )
            .order_by(OAuthApplication.id)
            .limit(1)
            .get()
        )
    except OAuthApplication.DoesNotExist:
        return create_application(
            org,
            name,
            application_uri="",
            redirect_uri="",
            description=BOOTSTRAP_APP_DESCRIPTION,
        )


def create_oauth_api_token(
    application, user_obj, scope, expiration_seconds=DEFAULT_TOKEN_EXPIRATION_SECONDS
):
    """
    Creates an OAuth access token with bootstrap metadata fields populated.

    Args:
        application: OAuthApplication instance
        user_obj: User instance used as the authorized_user
        scope: Space-separated scope string
        expiration_seconds: Token lifetime in seconds (default: 10 years)

    Returns:
        Tuple of (OAuthAccessToken, access_token_string)
    """
    return create_user_access_token_for_application(
        user_obj,
        application,
        scope,
        "Bearer",
        expiration_seconds,
        access_token=utils.random_ascii_string(40),
    )


def count_active_tokens(application):
    return (
        OAuthAccessToken.select()
        .where(
            OAuthAccessToken.application == application,
            OAuthAccessToken.expires_at > datetime.utcnow(),
        )
        .count()
    )


def create_oauth_api_token_under_limit(
    application,
    user,
    scope,
    expiration_seconds=DEFAULT_TOKEN_EXPIRATION_SECONDS,
    max_active_tokens=MAX_TOKENS_PER_APPLICATION,
):
    """Create an OAuth access token while atomically enforcing the active-token limit."""
    with db_transaction():
        locked_application = db_for_update(
            OAuthApplication.select().where(OAuthApplication.id == application.id)
        ).get()

        if count_active_tokens(locked_application) >= max_active_tokens:
            raise TokenLimitExceeded()

        return create_oauth_api_token(
            application=locked_application,
            user_obj=user,
            scope=scope,
            expiration_seconds=expiration_seconds,
        )


def list_application_tokens(application, page_token=None, limit=50):
    query = (
        OAuthAccessToken.select(OAuthAccessToken, User)
        .join(User, JOIN.LEFT_OUTER, on=(OAuthAccessToken.authorized_user == User.id))
        .switch(OAuthAccessToken)
        .where(OAuthAccessToken.application == application)
    )
    return paginate(query, OAuthAccessToken, descending=True, page_token=page_token, limit=limit)


def delete_application_token(application, token_uuid):
    try:
        token = OAuthAccessToken.get(
            OAuthAccessToken.application == application,
            OAuthAccessToken.uuid == token_uuid,
        )
        token.delete_instance()
        return True
    except OAuthAccessToken.DoesNotExist:
        return False


def create_application(org, name, application_uri, redirect_uri, **kwargs):
    client_secret = kwargs.pop("client_secret", random_string_generator(length=40)())
    return OAuthApplication.create(
        organization=org,
        name=name,
        application_uri=application_uri,
        redirect_uri=redirect_uri,
        secure_client_secret=DecryptedValue(client_secret),
        **kwargs,
    )


def validate_access_token(access_token):
    assert isinstance(access_token, str)
    token_name = access_token[:ACCESS_TOKEN_PREFIX_LENGTH]
    if not token_name:
        return None

    token_code = access_token[ACCESS_TOKEN_PREFIX_LENGTH:]
    if not token_code:
        return None

    try:
        found = (
            OAuthAccessToken.select(OAuthAccessToken, User)
            .join(User, on=(OAuthAccessToken.authorized_user == User.id))
            .where(OAuthAccessToken.token_name == token_name)
            .get()
        )

        if found.token_code is None or not found.token_code.matches(token_code):
            return None

        return found
    except OAuthAccessToken.DoesNotExist:
        pass

    return None


def validate_bootstrap_token(access_token, app_config=None):
    """Validate a token belongs to the configured bootstrap token owner.

    Expiration is intentionally skipped so the renew endpoint can decide whether
    to allow an expired token based on request locality.
    """
    if app_config is None:
        app_config = config.app_config or {}

    found = validate_access_token(access_token)
    if found is None:
        return None

    if found.application.name != get_bootstrap_app_name(app_config):
        return None

    owner = app_config.get("BOOTSTRAP_TOKEN_OWNER")
    superusers = set(app_config.get("SUPER_USERS") or [])
    if not owner or owner not in superusers:
        return None

    if found.application.organization.username != owner:
        return None

    if found.authorized_user.username != owner:
        return None

    return found


def get_bootstrap_tokens(application):
    """Return all tokens for the given application."""
    return list(OAuthAccessToken.select().where(OAuthAccessToken.application == application))


def delete_other_bootstrap_tokens(application, keep_token_id=None):
    """Delete tokens for the given bootstrap application except the ID to keep."""
    for token in get_bootstrap_tokens(application):
        if token.id != keep_token_id:
            token.delete_instance()


def lock_bootstrap_token_operation():
    """Serialize bootstrap token mutations with a transaction-scoped DB lock."""
    db_advisory_xact_lock(BOOTSTRAP_TOKEN_LOCK_ID)


def delete_token_by_id(token_id):
    """Delete a specific OAuthAccessToken by its primary key."""
    OAuthAccessToken.delete().where(OAuthAccessToken.id == token_id).execute()


def lookup_application_by_name(org, name):
    """Look up an OAuthApplication by organization and name. Returns None if not found."""
    try:
        return OAuthApplication.get(
            OAuthApplication.organization == org,
            OAuthApplication.name == name,
        )
    except OAuthApplication.DoesNotExist:
        return None


def lookup_applications_by_name(name):
    """Return all OAuthApplications matching the given name, regardless of owner."""
    return list(OAuthApplication.select().where(OAuthApplication.name == name))


def get_application_for_client_id(client_id):
    try:
        return OAuthApplication.get(client_id=client_id)
    except OAuthApplication.DoesNotExist:
        return None


def reset_client_secret(application):
    client_secret = random_string_generator(length=40)()
    application.secure_client_secret = DecryptedValue(client_secret)
    application.save()
    return application


def lookup_application(org, client_id):
    try:
        return OAuthApplication.get(organization=org, client_id=client_id)
    except OAuthApplication.DoesNotExist:
        return None


def delete_application(org, client_id):
    with db_transaction():
        application = lookup_application(org, client_id)
        if not application:
            return

        OauthAssignedToken.delete().where(OauthAssignedToken.application == application).execute()

        application.delete_instance(recursive=True, delete_nullable=True)
        return application


def lookup_access_token_by_uuid(token_uuid):
    try:
        return OAuthAccessToken.get(OAuthAccessToken.uuid == token_uuid)
    except OAuthAccessToken.DoesNotExist:
        return None


def lookup_access_token_for_user(user_obj, token_uuid):
    try:
        return (
            OAuthAccessToken.select(OAuthAccessToken, User)
            .join(User, on=(OAuthAccessToken.authorized_user == User.id))
            .where(
                OAuthAccessToken.authorized_user == user_obj, OAuthAccessToken.uuid == token_uuid
            )
            .get()
        )
    except OAuthAccessToken.DoesNotExist:
        return None


def list_access_tokens_for_user(user_obj):
    query = (
        OAuthAccessToken.select()
        .join(OAuthApplication)
        .switch(OAuthAccessToken)
        .join(User, on=(OAuthAccessToken.authorized_user == User.id))
        .where(OAuthAccessToken.authorized_user == user_obj)
    )

    return query


def get_assigned_authorization_for_user(user_obj, uuid):
    try:
        assigned_token = (
            OauthAssignedToken.select()
            .join(OAuthApplication)
            .where(OauthAssignedToken.assigned_user == user_obj, OauthAssignedToken.uuid == uuid)
            .get()
        )
        return assigned_token
    except OauthAssignedToken.DoesNotExist:
        return None


def list_assigned_authorizations_for_user(user_obj):
    query = (
        OauthAssignedToken.select()
        .join(OAuthApplication)
        .where(OauthAssignedToken.assigned_user == user_obj)
    )

    return query


def list_applications_for_org(org):
    query = OAuthApplication.select().join(User).where(OAuthApplication.organization == org)

    return query


def get_oauth_application_for_client_id(client_id):
    try:
        return (
            OAuthApplication.select()
            .join(User)
            .where(OAuthApplication.client_id == client_id)
            .get()
        )
    except OAuthApplication.DoesNotExist:
        return None


def create_user_access_token(user_obj, client_id, scope, access_token=None, expires_in=9000):
    application = get_application_for_client_id(client_id)
    return create_user_access_token_for_application(
        user_obj,
        application,
        scope,
        "token",
        expires_in,
        access_token=access_token,
    )


def create_user_access_token_for_application(
    user_obj, application, scope, token_type, expires_in, access_token=None
):
    access_token = access_token or random_string_generator(length=40)()
    token_name = access_token[:ACCESS_TOKEN_PREFIX_LENGTH]
    token_code = access_token[ACCESS_TOKEN_PREFIX_LENGTH:]

    assert len(token_name) == ACCESS_TOKEN_PREFIX_LENGTH
    assert len(token_code) >= ACCESS_TOKEN_MINIMUM_CODE_LENGTH

    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    created = OAuthAccessToken.create(
        application=application,
        authorized_user=user_obj,
        scope=scope,
        token_type=token_type,
        access_token="",
        token_code=Credential.from_string(token_code),
        token_name=token_name,
        expires_at=expires_at,
        data="",
    )
    return created, access_token


def assign_token_to_user(application, user, redirect_uri, scope, response_type):
    with db_transaction():
        token = OauthAssignedToken.create(
            application=application,
            assigned_user=user,
            redirect_uri=redirect_uri,
            scope=scope,
            response_type=response_type,
        )

        notification.create_notification(
            "assigned_authorization",
            user,
            {
                "username": user.username,
            },
        )

    return token


def get_token_assignment(uuid, db_user, org):
    if uuid is None:
        return None

    try:
        return (
            OauthAssignedToken.select()
            .join(OAuthApplication)
            .where(
                OauthAssignedToken.uuid == uuid,
                OauthAssignedToken.assigned_user == db_user,
                OAuthApplication.organization == org,
            )
            .get()
        )
    except OauthAssignedToken.DoesNotExist:
        return None


def get_token_assignment_for_client_id(uuid, user, client_id):
    try:
        return (
            OauthAssignedToken.select()
            .join(OAuthApplication)
            .where(
                OauthAssignedToken.uuid == uuid,
                OauthAssignedToken.assigned_user == user,
                OAuthApplication.client_id == client_id,
            )
            .get()
        )
    except OauthAssignedToken.DoesNotExist:
        return None
