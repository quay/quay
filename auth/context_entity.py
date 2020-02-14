from abc import ABCMeta, abstractmethod
from six import add_metaclass
from enum import Enum

from data import model

from auth.credential_consts import (
    ACCESS_TOKEN_USERNAME,
    OAUTH_TOKEN_USERNAME,
    APP_SPECIFIC_TOKEN_USERNAME,
)


class ContextEntityKind(Enum):
    """
    Defines the various kinds of entities in an auth context.

    Note that the string values of these fields *must* match the names of the fields in the
    ValidatedAuthContext class, as we fill them in directly based on the string names here.
    """

    anonymous = "anonymous"
    user = "user"
    robot = "robot"
    token = "token"
    oauthtoken = "oauthtoken"
    appspecifictoken = "appspecifictoken"
    signed_data = "signed_data"


@add_metaclass(ABCMeta)
class ContextEntityHandler(object):
    """
    Interface that represents handling specific kinds of entities under an auth context.
    """

    @abstractmethod
    def credential_username(self, entity_reference):
        """
        Returns the username to create credentials for this entity, if any.
        """
        pass

    @abstractmethod
    def get_serialized_entity_reference(self, entity_reference):
        """
        Returns the entity reference for this kind of auth context, serialized into a form that can
        be placed into a JSON object and put into a JWT.

        This is typically a DB UUID or another unique identifier for the object in the DB.
        """
        pass

    @abstractmethod
    def deserialize_entity_reference(self, serialized_entity_reference):
        """
        Returns the deserialized reference to the entity in the database, or None if none.
        """
        pass

    @abstractmethod
    def description(self, entity_reference):
        """
        Returns a human-readable and *public* description of the current entity.
        """
        pass

    @abstractmethod
    def analytics_id_and_public_metadata(self, entity_reference):
        """
        Returns the analyitics ID and a dict of public metadata for the current entity.
        """
        pass


class AnonymousEntityHandler(ContextEntityHandler):
    def credential_username(self, entity_reference):
        return None

    def get_serialized_entity_reference(self, entity_reference):
        return None

    def deserialize_entity_reference(self, serialized_entity_reference):
        return None

    def description(self, entity_reference):
        return "anonymous"

    def analytics_id_and_public_metadata(self, entity_reference):
        return "anonymous", {}


class UserEntityHandler(ContextEntityHandler):
    def credential_username(self, entity_reference):
        return entity_reference.username

    def get_serialized_entity_reference(self, entity_reference):
        return entity_reference.uuid

    def deserialize_entity_reference(self, serialized_entity_reference):
        return model.user.get_user_by_uuid(serialized_entity_reference)

    def description(self, entity_reference):
        return "user %s" % entity_reference.username

    def analytics_id_and_public_metadata(self, entity_reference):
        return entity_reference.username, {"username": entity_reference.username,}


class RobotEntityHandler(ContextEntityHandler):
    def credential_username(self, entity_reference):
        return entity_reference.username

    def get_serialized_entity_reference(self, entity_reference):
        return entity_reference.username

    def deserialize_entity_reference(self, serialized_entity_reference):
        return model.user.lookup_robot(serialized_entity_reference)

    def description(self, entity_reference):
        return "robot %s" % entity_reference.username

    def analytics_id_and_public_metadata(self, entity_reference):
        return entity_reference.username, {"username": entity_reference.username, "is_robot": True,}


class TokenEntityHandler(ContextEntityHandler):
    def credential_username(self, entity_reference):
        return ACCESS_TOKEN_USERNAME

    def get_serialized_entity_reference(self, entity_reference):
        return entity_reference.get_code()

    def deserialize_entity_reference(self, serialized_entity_reference):
        return model.token.load_token_data(serialized_entity_reference)

    def description(self, entity_reference):
        return "token %s" % entity_reference.friendly_name

    def analytics_id_and_public_metadata(self, entity_reference):
        return "token:%s" % entity_reference.id, {"token": entity_reference.friendly_name,}


class OAuthTokenEntityHandler(ContextEntityHandler):
    def credential_username(self, entity_reference):
        return OAUTH_TOKEN_USERNAME

    def get_serialized_entity_reference(self, entity_reference):
        return entity_reference.uuid

    def deserialize_entity_reference(self, serialized_entity_reference):
        return model.oauth.lookup_access_token_by_uuid(serialized_entity_reference)

    def description(self, entity_reference):
        return "oauthtoken for user %s" % entity_reference.authorized_user.username

    def analytics_id_and_public_metadata(self, entity_reference):
        return (
            "oauthtoken:%s" % entity_reference.id,
            {
                "oauth_token_id": entity_reference.id,
                "oauth_token_application_id": entity_reference.application.client_id,
                "oauth_token_application": entity_reference.application.name,
                "username": entity_reference.authorized_user.username,
            },
        )


class AppSpecificTokenEntityHandler(ContextEntityHandler):
    def credential_username(self, entity_reference):
        return APP_SPECIFIC_TOKEN_USERNAME

    def get_serialized_entity_reference(self, entity_reference):
        return entity_reference.uuid

    def deserialize_entity_reference(self, serialized_entity_reference):
        return model.appspecifictoken.get_token_by_uuid(serialized_entity_reference)

    def description(self, entity_reference):
        tpl = (entity_reference.title, entity_reference.user.username)
        return "app specific token %s for user %s" % tpl

    def analytics_id_and_public_metadata(self, entity_reference):
        return (
            "appspecifictoken:%s" % entity_reference.id,
            {
                "app_specific_token": entity_reference.uuid,
                "app_specific_token_title": entity_reference.title,
                "username": entity_reference.user.username,
            },
        )


class SignedDataEntityHandler(ContextEntityHandler):
    def credential_username(self, entity_reference):
        return None

    def get_serialized_entity_reference(self, entity_reference):
        raise NotImplementedError

    def deserialize_entity_reference(self, serialized_entity_reference):
        raise NotImplementedError

    def description(self, entity_reference):
        return "signed"

    def analytics_id_and_public_metadata(self, entity_reference):
        return "signed", {"signed": entity_reference}


CONTEXT_ENTITY_HANDLERS = {
    ContextEntityKind.anonymous: AnonymousEntityHandler,
    ContextEntityKind.user: UserEntityHandler,
    ContextEntityKind.robot: RobotEntityHandler,
    ContextEntityKind.token: TokenEntityHandler,
    ContextEntityKind.oauthtoken: OAuthTokenEntityHandler,
    ContextEntityKind.appspecifictoken: AppSpecificTokenEntityHandler,
    ContextEntityKind.signed_data: SignedDataEntityHandler,
}
