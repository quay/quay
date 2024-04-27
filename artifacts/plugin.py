from flask.testing import FlaskClient

from data.registry_model import registry_model
from endpoints.v2 import NameUnknown


class BaseArtifactPlugin(object):
    def __init__(self, plugin_name: str):
        self.name = plugin_name

    def register_routes(self, app):
        raise NotImplementedError("You must implement the init_routes method")

    def register_workers(self):
        raise NotImplementedError("You must implement the init_workers method")

    def __str__(self):
        return self.name


def get_artifact_repository(namespace_name, artifact_name):
    repository_ref = registry_model.lookup_repository(namespace_name, artifact_name)
    if repository_ref is None:
        raise NameUnknown("repository not found")
    return repository_ref


def create_artifact_repository(namespace_name, artifact_name):
    # TODO: Parse the namespace and artifact name
    # TODO: check if the name is a proper valid name (no special characters, etc)

    # TODO check auth permissions (see _authorize_or_downscope_request)
    # TODO create the repository
    # TODO return the repository
    pass


class ArtifactPluginQuayClient(FlaskClient):
    def __init__(self, plugin_name: str, *args, **kwargs):
        self.name = plugin_name
        super().__init__(*args, **kwargs)

    def create_artifact_repository(self, namespace_name, artifact_name):
        pass

    def create_artifact_manifest(self):
        pass

    def push_artifact_manifest(self):
        pass

    def tag_artifact_manifest(self):
        pass

    def upload_artifact(self):
        pass

    def get_artifact_repo(artifact_name: str):
        pass
