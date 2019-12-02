from data import model
from endpoints.common_models_interface import User, EndpointsCommonDataInterface


class EndpointsCommonDataPreOCIModel(EndpointsCommonDataInterface):
    def get_user(self, user_uuid):
        user = model.user.get_user_by_uuid(user_uuid)
        if user is None:
            return None

        return User(
            uuid=user.uuid,
            username=user.username,
            email=user.email,
            given_name=user.given_name,
            family_name=user.family_name,
            company=user.company,
            location=user.location,
        )

    def get_namespace_uuid(self, namespace_name):
        user = model.user.get_namespace_user(namespace_name)
        if user is None:
            return None

        return user.uuid


pre_oci_model = EndpointsCommonDataPreOCIModel()
