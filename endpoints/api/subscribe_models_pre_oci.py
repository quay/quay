from data.model.notification import create_unique_notification, delete_notifications_by_kind
from data.model.user import get_private_repo_count, get_user_or_org
from endpoints.api.subscribe_models_interface import SubscribeInterface


class PreOCIModel(SubscribeInterface):
    """
    PreOCIModel implements the data model for build triggers using a database schema before it was
    changed to support the OCI specification.
    """

    def get_private_repo_count(self, username):
        return get_private_repo_count(username)

    def create_unique_notification(self, kind_name, target_username, metadata={}):
        target = get_user_or_org(target_username)
        create_unique_notification(kind_name, target, metadata)

    def delete_notifications_by_kind(self, target_username, kind_name):
        target = get_user_or_org(target_username)
        delete_notifications_by_kind(target, kind_name)


data_model = PreOCIModel()
