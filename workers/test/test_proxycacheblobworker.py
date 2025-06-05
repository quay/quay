from test.fixtures import *
from workers.proxycacheblobworker import ProxyCacheBlobWorker


@pytest.fixture()
def proxy_cache_blob_worker():
    return ProxyCacheBlobWorker(None)


def test_proxy_cache_blob_download(proxy_cache_blob_worker, storage, app):
    assert not proxy_cache_blob_worker.blob_exists(
        "sha256:e692418e4cbaf90ca69d05a66403747baa33ee08806650b51fab815ad7fc331f", 1
    )
