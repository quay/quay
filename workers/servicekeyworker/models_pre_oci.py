from data import model
from workers.servicekeyworker.models_interface import ServiceKeyWorkerDataInterface


class PreOCIModel(ServiceKeyWorkerDataInterface):
    def set_key_expiration(self, kid, expiration_date):
        model.service_keys.set_key_expiration(kid, expiration_date)

    def create_service_key_for_testing(self, expiration):
        key = model.service_keys.create_service_key("test", "somekid", "quay", "", {}, expiration)
        return key.kid

    def get_service_key_expiration(self, kid):
        try:
            key = model.service_keys.get_service_key(kid, approved_only=False)
            return key.expiration_date
        except model.ServiceKeyDoesNotExist:
            return None


pre_oci_model = PreOCIModel()
