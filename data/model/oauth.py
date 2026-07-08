from __future__ import annotations

import json
import logging
import posixpath
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import unquote, urlparse

from flask import url_for
from peewee import PeeweeException

import features
from auth import scopes
from data.database import (
    OAuthAccessToken,
    OAuthApplication,
    OauthAssignedToken,
    OAuthAuthorizationCode,
    User,
    compute_advisory_lock_id,
    db_advisory_xact_lock,
    random_string_generator,
)
from data.fields import Credential, DecryptedValue
from data.model import config, db_transaction, notification, user
from data.model.organization import is_org_admin
from data.readreplica import ReadOnlyModeException
from oauth import utils
from oauth.provider import AuthorizationProvider
from util import get_app_url

logger = logging.getLogger(__name__)

ACCESS_TOKEN_PREFIX_LENGTH = 20
ACCESS_TOKEN_MINIMUM_CODE_LENGTH = 20
AUTHORIZATION_CODE_PREFIX_LENGTH = 20
DEFAULT_TOKEN_EXPIRATION_SECONDS = int(60 * 60 * 24 * 365.25 * 10)  # 10 years
BOOTSTRAP_APP_NAME = "__quay_bootstrap_app"
BOOTSTRAP_APP_DESCRIPTION = "Auto-created by bootstrap token provisioning"
BOOTSTRAP_TOKEN_DATA_KIND = "bootstrap"
BOOTSTRAP_TOKEN_LOCK_ID = compute_advisory_lock_id("bootstrap_token", 0)


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
            .join(User)
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
        # Check for a valid client ID.
        oauth_application = self.get_application_for_client_id(client_id)
        if oauth_application is None:
            return self._make_json_error_response("unauthorized_client")

        # Check for a valid redirect URI.
        is_valid_redirect_uri = self.validate_redirect_uri(client_id, redirect_uri)
        if not is_valid_redirect_uri:
            return self._invalid_redirect_uri_response()

        # Ensure proper response_type
        if response_type != "token":
            err = "unsupported_response_type"
            return self._make_redirect_error_response(redirect_uri, err)

        # Check conditions
        is_valid_access = self.validate_access()
        scope = params.get("scope", "")
        are_valid_scopes = self.validate_scope(client_id, scope)

        user_obj = self.get_authorized_user()
        token_assignment = get_token_assignment_for_request(
            assignment_uuid,
            user_obj,
            client_id,
            redirect_uri,
            response_type,
            scope,
        )

        # If PUBLIC_OAUTH_APPS is disabled, require org admin or an exact token assignment.
        if not features.PUBLIC_OAUTH_APPS and not (
            is_org_admin(user_obj, oauth_application.organization) or token_assignment is not None
        ):
            err = "unauthorized_client"
            return self._make_redirect_error_response(redirect_uri, err)

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

        # Check for an exact assignment and delete it if it exists.
        if token_assignment is not None:
            token_assignment.delete_instance()

        url = utils.build_url(redirect_uri, params)
        url += "#access_token=%s&token_type=%s&expires_in=%s" % (
            access_token,
            token_type,
            expires_in,
        )

        return self._make_response(headers={"Location": url}, status_code=302)

    def get_authorization_code(self, response_type, client_id, redirect_uri, **params):
        # Check for a valid client ID.
        oauth_application = self.get_application_for_client_id(client_id)
        if oauth_application is None:
            return self._make_json_error_response("unauthorized_client")

        # Check for a valid redirect URI before redirecting any error to the client.
        is_valid_redirect_uri = self.validate_redirect_uri(client_id, redirect_uri)
        if not is_valid_redirect_uri:
            return self._invalid_redirect_uri_response()

        # Ensure proper response_type.
        if response_type != "code":
            err = "unsupported_response_type"
            return self._make_redirect_error_response(redirect_uri, err)

        # If PUBLIC_OAUTH_APPS is disabled, code grants require org admin approval.
        if not features.PUBLIC_OAUTH_APPS and not is_org_admin(
            self.get_authorized_user(), oauth_application.organization
        ):
            err = "unauthorized_client"
            return self._make_redirect_error_response(redirect_uri, err)

        is_valid_access = self.validate_access()
        scope = params.get("scope", "")
        is_valid_scope = self.validate_scope(client_id, scope)

        if not is_valid_access:
            err = "access_denied"
            return self._make_redirect_error_response(redirect_uri, err)

        if not is_valid_scope:
            err = "invalid_scope"
            return self._make_redirect_error_response(redirect_uri, err)

        code = self.generate_authorization_code()
        self.persist_authorization_code(client_id=client_id, code=code, scope=scope)

        params.update(
            {"code": code, "response_type": None, "client_id": None, "redirect_uri": None}
        )
        redirect = utils.build_url(redirect_uri, params)
        return self._make_response(headers={"Location": redirect}, status_code=302)

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


def get_bootstrap_app_name() -> str:
    """Return the reserved bootstrap OAuth application name."""
    return BOOTSTRAP_APP_NAME


def get_bootstrap_app_names() -> set[str]:
    """Return reserved bootstrap OAuth application names."""
    return {BOOTSTRAP_APP_NAME}


def is_bootstrap_app_name(name: str) -> bool:
    """Return whether name is reserved for bootstrap OAuth applications."""
    return name in get_bootstrap_app_names()


def create_bootstrap_application(name: str, org: User) -> OAuthApplication:
    """Create a bootstrap OAuth application for the owner."""
    return create_application(
        org,
        name,
        application_uri="",
        redirect_uri="",
        description=BOOTSTRAP_APP_DESCRIPTION,
    )


def _bootstrap_token_data(user_obj: User, application: OAuthApplication) -> str:
    """Return metadata stored with bootstrap-created OAuth access tokens."""
    return json.dumps(
        {
            "kind": BOOTSTRAP_TOKEN_DATA_KIND,
            "owner": user_obj.username,
            "application_name": application.name,
        }
    )


def create_bootstrap_oauth_api_token(
    application: OAuthApplication,
    user_obj: User,
    scope: str,
    expiration_seconds: int = DEFAULT_TOKEN_EXPIRATION_SECONDS,
) -> tuple[OAuthAccessToken, str]:
    """Create a bootstrap OAuth API access token for an application/user pair."""
    return create_user_access_token_for_application(
        user_obj,
        application,
        scope,
        "Bearer",
        expiration_seconds,
        data=_bootstrap_token_data(user_obj, application),
    )


def _bootstrap_token_data_json(token: OAuthAccessToken) -> dict[str, Any]:
    try:
        return json.loads(token.data or "{}")
    except (TypeError, ValueError):
        return {}


def is_bootstrap_oauth_token(
    token: OAuthAccessToken,
    user_obj: User | None = None,
    application: OAuthApplication | None = None,
) -> bool:
    """Return whether an OAuth access token has bootstrap token metadata."""
    token_data = _bootstrap_token_data_json(token)
    if token_data.get("kind") != BOOTSTRAP_TOKEN_DATA_KIND:
        return False

    if user_obj is not None and token_data.get("owner") != user_obj.username:
        return False

    if application is not None and token_data.get("application_name") != application.name:
        return False

    return True


def get_application_tokens(
    application: OAuthApplication, authorized_user: User | None = None
) -> list[OAuthAccessToken]:
    """Return all OAuth access tokens for the given application."""
    query = OAuthAccessToken.select().where(OAuthAccessToken.application == application)
    if authorized_user is not None:
        query = query.where(OAuthAccessToken.authorized_user == authorized_user)

    return list(query)


def get_bootstrap_tokens(
    application: OAuthApplication, authorized_user: User | None = None
) -> list[OAuthAccessToken]:
    """Return bootstrap-marked OAuth access tokens for the given application."""
    bootstrap_tokens = []
    application_tokens = get_application_tokens(application, authorized_user=authorized_user)
    for token in application_tokens:
        if is_bootstrap_oauth_token(token, user_obj=authorized_user, application=application):
            bootstrap_tokens.append(token)

    return bootstrap_tokens


def get_bootstrap_managed_applications() -> list[OAuthApplication]:
    """Return all fixed-name OAuth applications with bootstrap token metadata."""
    bootstrap_applications = []
    for application in lookup_bootstrap_named_applications():
        if get_bootstrap_tokens(application):
            bootstrap_applications.append(application)

    return bootstrap_applications


def delete_bootstrap_tokens(
    application: OAuthApplication, keep_token_id: int | None = None
) -> None:
    """Delete bootstrap-marked tokens for the application except the ID to keep."""
    ids_to_delete = [
        token.id for token in get_bootstrap_tokens(application) if token.id != keep_token_id
    ]
    if ids_to_delete:
        OAuthAccessToken.delete().where(OAuthAccessToken.id << ids_to_delete).execute()


def get_bootstrap_application_candidates(
    owner: User,
) -> tuple[OAuthApplication | None, list[OAuthApplication]]:
    """Return the canonical and duplicate bootstrap-managed apps for an owner.

    Applications are considered bootstrap-managed only when they are owned by the
    configured bootstrap owner, have the reserved bootstrap app name, and carry
    at least one bootstrap-marked token for that owner. Results are ordered by
    application ID descending through lookup_applications_by_name, so the first
    token-bearing app is the canonical app and the remaining token-bearing apps
    are duplicates.
    """
    bootstrap_application_name = get_bootstrap_app_name()
    applications = lookup_applications_by_name(owner, bootstrap_application_name)

    canonical_application: OAuthApplication | None = None
    duplicate_applications: list[OAuthApplication] = []
    for application in applications:
        bootstrap_tokens = get_bootstrap_tokens(application, authorized_user=owner)
        if not bootstrap_tokens:
            continue

        if canonical_application is None:
            canonical_application = application
            continue

        duplicate_applications.append(application)

    return canonical_application, duplicate_applications


def get_singleton_bootstrap_application_candidates(
    owner: User,
) -> tuple[OAuthApplication | None, list[OAuthApplication]]:
    """Return the current owner's canonical app and all stale global bootstrap apps.

    Programmatic bootstrap is a deployment-wide singleton. The configured owner
    can have one canonical fixed-name bootstrap-managed application; every other
    fixed-name application with bootstrap token metadata is stale.
    """
    canonical_application = None
    stale_applications = []
    for application in lookup_bootstrap_named_applications():
        bootstrap_tokens = get_bootstrap_tokens(application)
        if not bootstrap_tokens:
            continue

        owner_bootstrap_tokens = [
            token
            for token in bootstrap_tokens
            if token.authorized_user_id == owner.id
            and is_bootstrap_oauth_token(token, user_obj=owner)
        ]
        if (
            canonical_application is None
            and application.organization_id == owner.id
            and owner_bootstrap_tokens
        ):
            canonical_application = application
            continue

        stale_applications.append(application)

    return canonical_application, stale_applications


def get_canonical_bootstrap_application(owner: User) -> OAuthApplication | None:
    """Return the canonical bootstrap-managed app for an owner, if one exists."""
    # Assumes boot.py provisioning has already enforced singleton bootstrap app cleanup.
    canonical_application, _ = get_bootstrap_application_candidates(owner)
    return canonical_application


def _get_bootstrap_owner_for_validation(app_config: dict[str, Any]) -> User | None:
    owner_name = app_config.get("BOOTSTRAP_TOKEN_OWNER")
    if not owner_name:
        return None

    superusers = app_config.get("SUPER_USERS") or []
    if owner_name not in superusers:
        return None

    return user.get_user(owner_name)


def validate_bootstrap_token(
    access_token: str, app_config: dict[str, Any] | None = None
) -> OAuthAccessToken | None:
    """Validate a token belongs to the configured canonical bootstrap app."""
    if app_config is None:
        app_config = config.app_config or {}

    found = validate_access_token(access_token)
    if found is None:
        return None

    owner = _get_bootstrap_owner_for_validation(app_config)
    if owner is None:
        return None

    canonical_application = get_canonical_bootstrap_application(owner)
    if canonical_application is None:
        return None

    if found.application_id != canonical_application.id:
        return None

    if found.authorized_user_id != owner.id:
        return None

    if not is_bootstrap_oauth_token(found, user_obj=owner, application=canonical_application):
        return None

    return found


def lookup_applications_by_name(org, name):
    """Look up OAuthApplications by organization and name in newest-first order."""
    return list(
        OAuthApplication.select()
        .where(
            OAuthApplication.organization == org,
            OAuthApplication.name == name,
        )
        .order_by(OAuthApplication.id.desc())
    )


def lookup_bootstrap_named_applications():
    """Look up all OAuthApplications with the reserved bootstrap name newest-first."""
    return list(
        OAuthApplication.select()
        .where(OAuthApplication.name == BOOTSTRAP_APP_NAME)
        .order_by(OAuthApplication.id.desc())
    )


def lookup_application_by_name(org, name):
    """Look up the newest OAuthApplication by organization and name."""
    applications = lookup_applications_by_name(org, name)
    return applications[0] if applications else None


def delete_applications(applications):
    """Delete OAuth applications and their dependent OAuth rows."""
    for application in applications:
        OauthAssignedToken.delete().where(OauthAssignedToken.application == application).execute()
        application.delete_instance(recursive=True, delete_nullable=True)


def lock_bootstrap_token_operation() -> None:
    """Serialize bootstrap token mutations with a transaction-scoped DB lock."""
    db_advisory_xact_lock(BOOTSTRAP_TOKEN_LOCK_ID)


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


def update_oauth_token_last_accessed(token: OAuthAccessToken) -> None:
    """Update OAuth token last_accessed using OAuth-specific debounce config."""
    now = datetime.now()
    threshold = timedelta(
        seconds=config.app_config.get("OAUTH_TOKEN_LAST_ACCESSED_UPDATE_THRESHOLD_S", 60)
    )
    if token.last_accessed is not None and now - token.last_accessed < threshold:
        return

    try:
        (
            OAuthAccessToken.update(last_accessed=now)
            .where(OAuthAccessToken.id == token.id)
            .execute()
        )
        token.last_accessed = now
    except ReadOnlyModeException:
        pass
    except PeeweeException:
        strict_logging_disabled = config.app_config.get(
            "ALLOW_WITHOUT_STRICT_LOGGING"
        ) or config.app_config.get("ALLOW_PULLS_WITHOUT_STRICT_LOGGING")
        if strict_logging_disabled:
            logger.exception("update last_accessed for OAuth token failed")
        else:
            raise


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
            .join(User)
            .where(OAuthAccessToken.token_name == token_name)
            .get()
        )

        if found.token_code is None or not found.token_code.matches(token_code):
            return None

        if found.expires_at > datetime.now():
            update_oauth_token_last_accessed(found)

        return found
    except OAuthAccessToken.DoesNotExist:
        pass

    return None


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
            .join(User)
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
        .join(User)
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
        data="",
    )


def create_user_access_token_for_application(
    user_obj, application, scope, token_type, expires_in, access_token=None, data=""
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
        data=data,
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


def get_token_assignment_for_request(uuid, db_user, client_id, redirect_uri, response_type, scope):
    if uuid is None or response_type != "token" or not scopes.validate_scope_string(scope):
        return None

    try:
        assignment = (
            OauthAssignedToken.select()
            .join(OAuthApplication)
            .where(
                OauthAssignedToken.uuid == uuid,
                OauthAssignedToken.assigned_user == db_user,
                OAuthApplication.client_id == client_id,
                OauthAssignedToken.redirect_uri == redirect_uri,
                OauthAssignedToken.response_type == "token",
            )
            .get()
        )
    except OauthAssignedToken.DoesNotExist:
        return None

    if not scopes.is_subset_string(assignment.scope, scope):
        return None

    return assignment


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
