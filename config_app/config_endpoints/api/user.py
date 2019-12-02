from auth.auth_context import get_authenticated_user
from config_app.config_endpoints.api import resource, ApiResource, nickname
from config_app.config_endpoints.api.superuser_models_interface import user_view


@resource("/v1/user/")
class User(ApiResource):
    """ Operations related to users. """

    @nickname("getLoggedInUser")
    def get(self):
        """ Get user information for the authenticated user. """
        user = get_authenticated_user()
        return user_view(user)
