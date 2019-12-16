import logging

from abc import ABCMeta, abstractmethod
from cachetools.func import lru_cache
from six import add_metaclass

from app import app
from data import model

from flask_principal import Identity, identity_changed

from auth.auth_context import set_authenticated_context
from auth.context_entity import ContextEntityKind, CONTEXT_ENTITY_HANDLERS
from auth.permissions import QuayDeferredPermissionUser
from auth.scopes import scopes_from_scope_string

logger = logging.getLogger(__name__)


@add_metaclass(ABCMeta)
class AuthContext(object):
    """
    Interface that represents the current context of authentication.
    """

    @property
    @abstractmethod
    def entity_kind(self):
        """
        Returns the kind of the entity in this auth context.
        """
        pass

    @property
    @abstractmethod
    def is_anonymous(self):
        """
        Returns true if this is an anonymous context.
        """
        pass

    @property
    @abstractmethod
    def authed_oauth_token(self):
        """
        Returns the authenticated OAuth token, if any.
        """
        pass

    @property
    @abstractmethod
    def authed_user(self):
        """
        Returns the authenticated user, whether directly, or via an OAuth or access token.

        Note that this property will also return robot accounts.
        """
        pass

    @property
    @abstractmethod
    def has_nonrobot_user(self):
        """
        Returns whether a user (not a robot) was authenticated successfully.
        """
        pass

    @property
    @abstractmethod
    def identity(self):
        """
        Returns the identity for the auth context.
        """
        pass

    @property
    @abstractmethod
    def description(self):
        """
        Returns a human-readable and *public* description of the current auth context.
        """
        pass

    @property
    @abstractmethod
    def credential_username(self):
        """
        Returns the username to create credentials for this context's entity, if any.
        """
        pass

    @abstractmethod
    def analytics_id_and_public_metadata(self):
        """
        Returns the analytics ID and public log metadata for this auth context.
        """
        pass

    @abstractmethod
    def apply_to_request_context(self):
        """
        Applies this auth result to the auth context and Flask-Principal.
        """
        pass

    @abstractmethod
    def to_signed_dict(self):
        """
        Serializes the auth context into a dictionary suitable for inclusion in a JWT or other form
        of signed serialization.
        """
        pass

    @property
    @abstractmethod
    def unique_key(self):
        """
        Returns a key that is unique to this auth context type and its data.

        For example, an instance of the auth context type for the user might be a string of the form
        `user-{user-uuid}`. Callers should treat this key as opaque and not rely on the contents for
        anything besides uniqueness. This is typically used by callers when they'd like to check
        cache but not hit the database to get a fully validated auth context.
        """
        pass


class ValidatedAuthContext(AuthContext):
    """
    ValidatedAuthContext represents the loaded, authenticated and validated auth information for the
    current request context.
    """

    def __init__(
        self,
        user=None,
        token=None,
        oauthtoken=None,
        robot=None,
        appspecifictoken=None,
        signed_data=None,
    ):
        # Note: These field names *MUST* match the string values of the kinds defined in
        # ContextEntityKind.
        self.user = user
        self.robot = robot
        self.token = token
        self.oauthtoken = oauthtoken
        self.appspecifictoken = appspecifictoken
        self.signed_data = signed_data

    def tuple(self):
        return list(vars(self).values())

    def __eq__(self, other):
        return self.tuple() == other.tuple()

    @property
    def entity_kind(self):
        """
        Returns the kind of the entity in this auth context.
        """
        for kind in ContextEntityKind:
            if hasattr(self, kind.value) and getattr(self, kind.value):
                return kind

        return ContextEntityKind.anonymous

    @property
    def authed_user(self):
        """
        Returns the authenticated user, whether directly, or via an OAuth token.

        Note that this will also return robot accounts.
        """
        authed_user = self._authed_user()
        if authed_user is not None and not authed_user.enabled:
            logger.warning("Attempt to reference a disabled user/robot: %s", authed_user.username)
            return None

        return authed_user

    @property
    def authed_oauth_token(self):
        return self.oauthtoken

    def _authed_user(self):
        if self.oauthtoken:
            return self.oauthtoken.authorized_user

        if self.appspecifictoken:
            return self.appspecifictoken.user

        if self.signed_data:
            return model.user.get_user(self.signed_data["user_context"])

        return self.user if self.user else self.robot

    @property
    def is_anonymous(self):
        """
        Returns true if this is an anonymous context.
        """
        return not self.authed_user and not self.token and not self.signed_data

    @property
    def has_nonrobot_user(self):
        """
        Returns whether a user (not a robot) was authenticated successfully.
        """
        return bool(self.authed_user and not self.robot)

    @property
    def identity(self):
        """
        Returns the identity for the auth context.
        """
        if self.oauthtoken:
            scope_set = scopes_from_scope_string(self.oauthtoken.scope)
            return QuayDeferredPermissionUser.for_user(self.oauthtoken.authorized_user, scope_set)

        if self.authed_user:
            return QuayDeferredPermissionUser.for_user(self.authed_user)

        if self.token:
            return Identity(self.token.get_code(), "token")

        if self.signed_data:
            identity = Identity(None, "signed_grant")
            identity.provides.update(self.signed_data["grants"])
            return identity

        return None

    @property
    def entity_reference(self):
        """
        Returns the DB object reference for this context's entity.
        """
        if self.entity_kind == ContextEntityKind.anonymous:
            return None

        return getattr(self, self.entity_kind.value)

    @property
    def description(self):
        """
        Returns a human-readable and *public* description of the current auth context.
        """
        handler = CONTEXT_ENTITY_HANDLERS[self.entity_kind]()
        return handler.description(self.entity_reference)

    @property
    def credential_username(self):
        """
        Returns the username to create credentials for this context's entity, if any.
        """
        handler = CONTEXT_ENTITY_HANDLERS[self.entity_kind]()
        return handler.credential_username(self.entity_reference)

    def analytics_id_and_public_metadata(self):
        """
        Returns the analytics ID and public log metadata for this auth context.
        """
        handler = CONTEXT_ENTITY_HANDLERS[self.entity_kind]()
        return handler.analytics_id_and_public_metadata(self.entity_reference)

    def apply_to_request_context(self):
        """
        Applies this auth result to the auth context and Flask-Principal.
        """
        # Save to the request context.
        set_authenticated_context(self)

        # Set the identity for Flask-Principal.
        if self.identity:
            identity_changed.send(app, identity=self.identity)

    @property
    def unique_key(self):
        signed_dict = self.to_signed_dict()
        return "%s-%s" % (signed_dict["entity_kind"], signed_dict.get("entity_reference", "(anon)"))

    def to_signed_dict(self):
        """
        Serializes the auth context into a dictionary suitable for inclusion in a JWT or other form
        of signed serialization.
        """
        dict_data = {
            "version": 2,
            "entity_kind": self.entity_kind.value,
        }

        if self.entity_kind != ContextEntityKind.anonymous:
            handler = CONTEXT_ENTITY_HANDLERS[self.entity_kind]()
            dict_data.update(
                {
                    "entity_reference": handler.get_serialized_entity_reference(
                        self.entity_reference
                    ),
                }
            )

        # Add legacy information.
        # TODO: Remove this all once the new code is fully deployed.
        if self.token:
            dict_data.update(
                {"kind": "token", "token": self.token.get_code(),}
            )

        if self.oauthtoken:
            dict_data.update(
                {"kind": "oauth", "oauth": self.oauthtoken.uuid, "user": self.authed_user.username,}
            )

        if self.user or self.robot:
            dict_data.update(
                {"kind": "user", "user": self.authed_user.username,}
            )

        if self.appspecifictoken:
            dict_data.update(
                {"kind": "user", "user": self.authed_user.username,}
            )

        if self.is_anonymous:
            dict_data.update(
                {"kind": "anonymous",}
            )

        # End of legacy information.
        return dict_data


class SignedAuthContext(AuthContext):
    """
    SignedAuthContext represents an auth context loaded from a signed token of some kind, such as a
    JWT.

    Unlike ValidatedAuthContext, SignedAuthContext operates lazily, only loading the actual {user,
    robot, token, etc} when requested. This allows registry operations that only need to check if
    *some* entity is present to do so, without hitting the database.
    """

    def __init__(self, kind, signed_data, v1_dict_format):
        self.kind = kind
        self.signed_data = signed_data
        self.v1_dict_format = v1_dict_format

    @property
    def unique_key(self):
        if self.v1_dict_format:
            # Since V1 data format is verbose, just use the validated version to get the key.
            return self._get_validated().unique_key

        signed_dict = self.signed_data
        return "%s-%s" % (signed_dict["entity_kind"], signed_dict.get("entity_reference", "(anon)"))

    @classmethod
    def build_from_signed_dict(cls, dict_data, v1_dict_format=False):
        if not v1_dict_format:
            entity_kind = ContextEntityKind(dict_data.get("entity_kind", "anonymous"))
            return SignedAuthContext(entity_kind, dict_data, v1_dict_format)

        # Legacy handling.
        # TODO: Remove this all once the new code is fully deployed.
        kind_string = dict_data.get("kind", "anonymous")
        if kind_string == "oauth":
            kind_string = "oauthtoken"

        kind = ContextEntityKind(kind_string)
        return SignedAuthContext(kind, dict_data, v1_dict_format)

    @lru_cache(maxsize=1)
    def _get_validated(self):
        """
        Returns a ValidatedAuthContext for this signed context, resolving all the necessary
        references.
        """
        if not self.v1_dict_format:
            if self.kind == ContextEntityKind.anonymous:
                return ValidatedAuthContext()

            serialized_entity_reference = self.signed_data["entity_reference"]
            handler = CONTEXT_ENTITY_HANDLERS[self.kind]()
            entity_reference = handler.deserialize_entity_reference(serialized_entity_reference)
            if entity_reference is None:
                logger.debug(
                    "Could not deserialize entity reference `%s` under kind `%s`",
                    serialized_entity_reference,
                    self.kind,
                )
                return ValidatedAuthContext()

            return ValidatedAuthContext(**{self.kind.value: entity_reference})

        # Legacy handling.
        # TODO: Remove this all once the new code is fully deployed.
        kind_string = self.signed_data.get("kind", "anonymous")
        if kind_string == "oauth":
            kind_string = "oauthtoken"

        kind = ContextEntityKind(kind_string)
        if kind == ContextEntityKind.anonymous:
            return ValidatedAuthContext()

        if kind == ContextEntityKind.user or kind == ContextEntityKind.robot:
            user = model.user.get_user(self.signed_data.get("user", ""))
            if not user:
                return None

            return (
                ValidatedAuthContext(robot=user) if user.robot else ValidatedAuthContext(user=user)
            )

        if kind == ContextEntityKind.token:
            token = model.token.load_token_data(self.signed_data.get("token"))
            if not token:
                return None

            return ValidatedAuthContext(token=token)

        if kind == ContextEntityKind.oauthtoken:
            user = model.user.get_user(self.signed_data.get("user", ""))
            if not user:
                return None

            token_uuid = self.signed_data.get("oauth", "")
            oauthtoken = model.oauth.lookup_access_token_for_user(user, token_uuid)
            if not oauthtoken:
                return None

            return ValidatedAuthContext(oauthtoken=oauthtoken)

        raise Exception(
            "Unknown auth context kind `%s` when deserializing %s" % (kind, self.signed_data)
        )
        # End of legacy handling.

    @property
    def entity_kind(self):
        """
        Returns the kind of the entity in this auth context.
        """
        return self.kind

    @property
    def is_anonymous(self):
        """
        Returns true if this is an anonymous context.
        """
        return self.kind == ContextEntityKind.anonymous

    @property
    def authed_user(self):
        """
        Returns the authenticated user, whether directly, or via an OAuth or access token.

        Note that this property will also return robot accounts.
        """
        if self.kind == ContextEntityKind.anonymous:
            return None

        return self._get_validated().authed_user

    @property
    def authed_oauth_token(self):
        if self.kind == ContextEntityKind.anonymous:
            return None

        return self._get_validated().authed_oauth_token

    @property
    def has_nonrobot_user(self):
        """
        Returns whether a user (not a robot) was authenticated successfully.
        """
        if self.kind == ContextEntityKind.anonymous:
            return False

        return self._get_validated().has_nonrobot_user

    @property
    def identity(self):
        """
        Returns the identity for the auth context.
        """
        return self._get_validated().identity

    @property
    def description(self):
        """
        Returns a human-readable and *public* description of the current auth context.
        """
        return self._get_validated().description

    @property
    def credential_username(self):
        """
        Returns the username to create credentials for this context's entity, if any.
        """
        return self._get_validated().credential_username

    def analytics_id_and_public_metadata(self):
        """
        Returns the analytics ID and public log metadata for this auth context.
        """
        return self._get_validated().analytics_id_and_public_metadata()

    def apply_to_request_context(self):
        """
        Applies this auth result to the auth context and Flask-Principal.
        """
        return self._get_validated().apply_to_request_context()

    def to_signed_dict(self):
        """
        Serializes the auth context into a dictionary suitable for inclusion in a JWT or other form
        of signed serialization.
        """
        return self.signed_data
