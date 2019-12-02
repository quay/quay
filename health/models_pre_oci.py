from data.model import health
from health.models_interface import HealthCheckDataInterface


class PreOCIModel(HealthCheckDataInterface):
    def check_health(self, app_config):
        return health.check_health(app_config)


pre_oci_model = PreOCIModel()
