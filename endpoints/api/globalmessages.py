"""
Messages API.
"""
from flask import abort
from flask import make_response
from flask import request

import features
from auth import scopes
from auth.permissions import SuperUserPermission
from endpoints.api import (
    ApiResource,
    resource,
    nickname,
    require_fresh_login,
    verify_not_prod,
    validate_json_request,
    require_scope,
    show_if,
)
from .globalmessages_models_pre_oci import pre_oci_model as model


@resource("/v1/messages")
class GlobalUserMessages(ApiResource):
    """
    Resource for getting a list of super user messages.
    """

    schemas = {
        "GetMessage": {
            "id": "GetMessage",
            "type": "object",
            "description": "Messages that a super user has saved in the past",
            "properties": {
                "message": {
                    "type": "array",
                    "description": "A list of messages",
                    "itemType": {
                        "type": "object",
                        "properties": {
                            "uuid": {"type": "string", "description": "The message id",},
                            "content": {"type": "string", "description": "The actual message",},
                            "media_type": {
                                "type": "string",
                                "description": "The media type of the message",
                                "enum": ["text/plain", "text/markdown"],
                            },
                            "severity": {
                                "type": "string",
                                "description": "The severity of the message",
                                "enum": ["info", "warning", "error"],
                            },
                        },
                    },
                },
            },
        },
        "CreateMessage": {
            "id": "CreateMessage",
            "type": "object",
            "description": "Create a new message",
            "properties": {
                "message": {
                    "type": "object",
                    "description": "A single message",
                    "required": ["content", "media_type", "severity",],
                    "properties": {
                        "content": {"type": "string", "description": "The actual message",},
                        "media_type": {
                            "type": "string",
                            "description": "The media type of the message",
                            "enum": ["text/plain", "text/markdown"],
                        },
                        "severity": {
                            "type": "string",
                            "description": "The severity of the message",
                            "enum": ["info", "warning", "error"],
                        },
                    },
                },
            },
        },
    }

    @nickname("getGlobalMessages")
    def get(self):
        """
        Return a super users messages.
        """
        return {
            "messages": [m.to_dict() for m in model.get_all_messages()],
        }

    @require_fresh_login
    @verify_not_prod
    @nickname("createGlobalMessage")
    @validate_json_request("CreateMessage")
    @require_scope(scopes.SUPERUSER)
    def post(self):
        """
        Create a message.
        """
        if not features.SUPER_USERS:
            abort(404)

        if SuperUserPermission().can():
            message_req = request.get_json()["message"]
            message = model.create_message(
                message_req["severity"], message_req["media_type"], message_req["content"]
            )
            if message is None:
                abort(400)
            return make_response("", 201)

        abort(403)


@resource("/v1/message/<uuid>")
@show_if(features.SUPER_USERS)
class GlobalUserMessage(ApiResource):
    """
    Resource for managing individual messages.
    """

    @require_fresh_login
    @verify_not_prod
    @nickname("deleteGlobalMessage")
    @require_scope(scopes.SUPERUSER)
    def delete(self, uuid):
        """
        Delete a message.
        """
        if SuperUserPermission().can():
            model.delete_message(uuid)
            return make_response("", 204)

        abort(403)
