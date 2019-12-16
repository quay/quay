from .__init__models_interface import InitDataInterface

from data import model
from data.logs_model import logs_model


class PreOCIModel(InitDataInterface):
    def is_app_repository(self, namespace_name, repository_name):
        return (
            model.repository.get_repository(
                namespace_name, repository_name, kind_filter="application"
            )
            is not None
        )

    def repository_is_public(self, namespace_name, repository_name):
        return model.repository.repository_is_public(namespace_name, repository_name)

    def log_action(self, kind, namespace_name, repository_name, performer, ip, metadata):
        repository = model.repository.get_repository(namespace_name, repository_name)
        logs_model.log_action(
            kind,
            namespace_name,
            performer=performer,
            ip=ip,
            metadata=metadata,
            repository=repository,
        )


pre_oci_model = PreOCIModel()
