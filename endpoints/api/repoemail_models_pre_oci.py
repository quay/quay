from data import model
from endpoints.api.repoemail_models_interface import (
    RepoEmailDataInterface,
    RepositoryAuthorizedEmail,
)


def _return_none_or_data(func, namespace_name, repository_name, email):
    data = func(namespace_name, repository_name, email)
    if data is None:
        return data
    return RepositoryAuthorizedEmail(
        email, repository_name, namespace_name, data.confirmed, data.code
    )


class PreOCIModel(RepoEmailDataInterface):
    """
    PreOCIModel implements the data model for the Repo Email using a database schema before it was
    changed to support the OCI specification.
    """

    def get_email_authorized_for_repo(self, namespace_name, repository_name, email):
        return _return_none_or_data(
            model.repository.get_email_authorized_for_repo, namespace_name, repository_name, email
        )

    def create_email_authorization_for_repo(self, namespace_name, repository_name, email):
        return _return_none_or_data(
            model.repository.create_email_authorization_for_repo,
            namespace_name,
            repository_name,
            email,
        )


pre_oci_model = PreOCIModel()
