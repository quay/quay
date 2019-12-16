from urllib.parse import urljoin

from flask import url_for


def get_blob_download_uri_getter(context, url_scheme_and_hostname):
    """
    Returns a function with context to later generate the uri for a download blob.

    :param context: Flask RequestContext
    :param url_scheme_and_hostname: URLSchemeAndHostname class instance
    :return: function (repository_and_namespace, checksum) -> uri
    """

    def create_uri(repository_and_namespace, checksum):
        """
        Creates a uri for a download blob from a repository, namespace, and checksum from earlier
        context.
        """
        with context:
            relative_layer_url = url_for(
                "v2.download_blob", repository=repository_and_namespace, digest=checksum
            )
        return urljoin(url_scheme_and_hostname.get_url(), relative_layer_url)

    return create_uri
