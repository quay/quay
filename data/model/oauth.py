import json
import logging
from datetime import datetime, timedelta

from flask import url_for

from auth import scopes
from data.database import (
    OAuthAccessToken,
    OAuthApplication,
    OauthAssignedToken,
    OAuthAuthorizationCode,
    User,
    random_string_generator,
)
from data.fields import Credential, DecryptedValue
from data.model import config, db_transaction, notification, user
from data.model.organization import is_org_admin
from oauth import utils
from oauth.provider import AuthorizationProvider
from util import get_app_url

logger = logging.getLogger(__name__)

ACCESS_TOKEN_PREFIX_LENGTH = 20
ACCESS_TOKEN_MINIMUM_CODE_LENGTH = 20
AUTHORIZATION_CODE_PREFIX_LENGTH = 20


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
        return int(60 * 60 * 24 * 365.25 * 10)  # 10 Years

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

        if redirect_uri == internal_redirect_url:
            return True

        try:
            oauth_app = OAuthApplication.get(client_id=client_id)
            if (
                oauth_app.redirect_uri
                and redirect_uri
                and redirect_uri.startswith(oauth_app.redirect_uri)
            ):
                return True
            return False
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
            .join(User)
            .where(OAuthAccessToken.token_name == token_name)
            .get()
        )

        if found.token_code is None or not found.token_code.matches(token_code):
            return None

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
    access_token = access_token or random_string_generator(length=40)()
    token_name = access_token[:ACCESS_TOKEN_PREFIX_LENGTH]
    token_code = access_token[ACCESS_TOKEN_PREFIX_LENGTH:]

    assert len(token_name) == ACCESS_TOKEN_PREFIX_LENGTH
    assert len(token_code) >= ACCESS_TOKEN_MINIMUM_CODE_LENGTH

    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    application = get_application_for_client_id(client_id)
    created = OAuthAccessToken.create(
        application=application,
        authorized_user=user_obj,
        scope=scope,
        token_type="token",
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
