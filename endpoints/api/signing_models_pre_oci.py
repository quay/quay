from data import model
from endpoints.api.signing_models_interface import SigningInterface


class PreOCIModel(SigningInterface):
    """
    PreOCIModel implements the data model for signing using a database schema before it was changed
    to support the OCI specification.
    """

    def is_trust_enabled(self, namespace_name, repo_name):
        repo = model.repository.get_repository(namespace_name, repo_name)
        if repo is None:
            return False

        return repo.trust_enabled


pre_oci_model = PreOCIModel()
