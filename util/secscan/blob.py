from urllib.parse import urljoin

from flask import url_for

from util.security.registry_jwt import generate_bearer_token, build_context_and_subject


def _repository_and_namespace(repository_ref):
    repo_name = repository_ref.name
    namespace_name = repository_ref.namespace_name
    return "/".join([namespace_name, repo_name])


class BlobURLRetriever(object):
    """
    Helper class which encodes the logic for retrieving blobs for security indexing.
    """

    def __init__(self, storage, instance_keys, app):
        assert storage is not None
        assert instance_keys is not None
        assert app is not None

        self._storage = storage
        self._instance_keys = instance_keys
        self._app = app

    def url_for_download(self, repository_ref, blob):
        """
        Returns the URL for downloading the given blob under the given repository.
        """
        # Try via direct download from storage.
        uri = self._storage.get_direct_download_url(self._storage.locations, blob.storage_path)
        if uri is not None:
            return uri

        # Otherwise, use the registry blob download endpoint.
        with self._app.test_request_context("/"):
            relative_layer_url = url_for(
                "v2.download_blob",
                repository=_repository_and_namespace(repository_ref),
                digest=blob.digest,
            )

        url_scheme_and_hostname = "%s://%s" % (
            self._app.config["PREFERRED_URL_SCHEME"],
            self._app.config["SERVER_HOSTNAME"],
        )
        return urljoin(url_scheme_and_hostname, relative_layer_url)

    def headers_for_download(self, repository_ref, blob, timeout=60):
        """
        Returns the headers for downloading the given blob under the given repository.
        """
        uri = self._storage.get_direct_download_url(self._storage.locations, blob.storage_path)
        if uri is not None:
            return {}

        # Otherwise, we mint a JWT and place it into an Auth header.
        audience = self._app.config["SERVER_HOSTNAME"]
        context, subject = build_context_and_subject()
        access = [
            {
                "type": "repository",
                "name": _repository_and_namespace(repository_ref),
                "actions": ["pull"],
            }
        ]
        assert set(act for acs in access for act in acs["actions"]) == {"pull"}

        auth_token = generate_bearer_token(
            audience, subject, context, access, timeout, self._instance_keys
        )

        return {"Authorization": ["Bearer " + auth_token.decode("ascii")]}
