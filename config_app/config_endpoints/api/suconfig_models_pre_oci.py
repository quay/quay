from data import model
from data.database import User
from config_app.config_endpoints.api.suconfig_models_interface import SuperuserConfigDataInterface


class PreOCIModel(SuperuserConfigDataInterface):
    # Note: this method is different than has_users: the user select will throw if the user
    # table does not exist, whereas has_users assumes the table is valid
    def is_valid(self):
        try:
            list(User.select().limit(1))
            return True
        except:
            return False

    def has_users(self):
        return bool(list(User.select().limit(1)))

    def create_superuser(self, username, password, email):
        return model.user.create_user(username, password, email, auto_verify=True).uuid

    def has_federated_login(self, username, service_name):
        user = model.user.get_user(username)
        if user is None:
            return False

        return bool(model.user.lookup_federated_login(user, service_name))

    def attach_federated_login(self, username, service_name, federated_username):
        user = model.user.get_user(username)
        if user is None:
            return False

        model.user.attach_federated_login(user, service_name, federated_username)


pre_oci_model = PreOCIModel()
