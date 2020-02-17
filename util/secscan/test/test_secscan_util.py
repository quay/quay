import pytest

from app import app
from util.config import URLSchemeAndHostname
from util.secscan.secscan_util import get_blob_download_uri_getter

from test.fixtures import *


@pytest.mark.parametrize(
    "url_scheme_and_hostname, repo_namespace, checksum, expected_value,",
    [
        (
            URLSchemeAndHostname("http", "localhost:5000"),
            "devtable/simple",
            "tarsum+sha256:123",
            "http://localhost:5000/v2/devtable/simple/blobs/tarsum%2Bsha256:123",
        ),
    ],
)
def test_blob_download_uri_getter(
    app, url_scheme_and_hostname, repo_namespace, checksum, expected_value
):
    blob_uri_getter = get_blob_download_uri_getter(
        app.test_request_context("/"), url_scheme_and_hostname
    )

    assert blob_uri_getter(repo_namespace, checksum) == expected_value
