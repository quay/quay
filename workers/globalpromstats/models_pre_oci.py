from data import model

from workers.globalpromstats.models_interface import GlobalPromStatsWorkerDataInterface


class PreOCIModel(GlobalPromStatsWorkerDataInterface):
    def get_repository_count(self):
        return model.repository.get_repository_count()

    def get_active_user_count(self):
        return model.user.get_active_user_count()

    def get_active_org_count(self):
        return model.organization.get_active_org_count()

    def get_robot_count(self):
        return model.user.get_robot_count()


pre_oci_model = PreOCIModel()
