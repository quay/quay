import logging

from auth.permissions import (
    UserAdminPermission,
    UserReadPermission,
    SuperUserPermission,
)
from endpoints.api import resource, ApiResource, nickname, require_scope
from auth.auth_context import get_authenticated_user
from endpoints.decorators import anon_allowed
from endpoints.exception import InvalidToken
from endpoints.api.v2 import API_V2_ORG_PATH
from data.model import user
from auth import scopes
from app import authentication

logger = logging.getLogger(__name__)


@resource(f"{API_V2_ORG_PATH}/user/")
class UserResource(ApiResource):
    @require_scope(scopes.READ_USER)
    @nickname("getUserSettings")
    @anon_allowed
    def get(self):
        authenticated_user = get_authenticated_user()
        username = authenticated_user.username
        if (
            authenticated_user is None
            or authenticated_user.organization
            or not UserReadPermission(username).can()
        ):
            raise InvalidToken("Requires authentication", payload={"session_required": False})

        user_response = user.feature_data(authenticated_user, SuperUserPermission)

        is_admin = UserAdminPermission(username).can()
        if is_admin:
            user_response.update(user.get_admin_user_response(authenticated_user, authentication))

        return user_response
