from storage.local import LocalStorage
from storage.cloud import (
    S3Storage,
    GoogleCloudStorage,
    RadosGWStorage,
    CloudFrontedS3Storage,
    RHOCSStorage,
)
from storage.fakestorage import FakeStorage
from storage.distributedstorage import DistributedStorage
from storage.swift import SwiftStorage
from storage.azurestorage import AzureStorage
from storage.downloadproxy import DownloadProxy
from util.ipresolver import NoopIPResolver

TYPE_LOCAL_STORAGE = "LocalStorage"

STORAGE_DRIVER_CLASSES = {
    "LocalStorage": LocalStorage,
    "S3Storage": S3Storage,
    "GoogleCloudStorage": GoogleCloudStorage,
    "RadosGWStorage": RadosGWStorage,
    "SwiftStorage": SwiftStorage,
    "CloudFrontedS3Storage": CloudFrontedS3Storage,
    "AzureStorage": AzureStorage,
    "RHOCSStorage": RHOCSStorage,
}


def get_storage_driver(location, chunk_cleanup_queue, config_provider, ip_resolver, storage_params):
    """
    Returns a storage driver class for the given storage configuration (a pair of string name and a
    dict of parameters).
    """
    driver = storage_params[0]
    parameters = storage_params[1]
    driver_class = STORAGE_DRIVER_CLASSES.get(driver, FakeStorage)
    context = StorageContext(location, chunk_cleanup_queue, config_provider, ip_resolver)
    return driver_class(context, **parameters)


class StorageContext(object):
    def __init__(self, location, chunk_cleanup_queue, config_provider, ip_resolver):
        self.location = location
        self.chunk_cleanup_queue = chunk_cleanup_queue
        self.config_provider = config_provider
        self.ip_resolver = ip_resolver or NoopIPResolver()


class Storage(object):
    def __init__(
        self,
        app=None,
        chunk_cleanup_queue=None,
        instance_keys=None,
        config_provider=None,
        ip_resolver=None,
    ):
        self.app = app
        if app is not None:
            self.state = self.init_app(
                app, chunk_cleanup_queue, instance_keys, config_provider, ip_resolver
            )
        else:
            self.state = None

    def init_app(self, app, chunk_cleanup_queue, instance_keys, config_provider, ip_resolver):
        storages = {}
        for location, storage_params in list(app.config.get("DISTRIBUTED_STORAGE_CONFIG").items()):
            storages[location] = get_storage_driver(
                location, chunk_cleanup_queue, config_provider, ip_resolver, storage_params,
            )

        preference = app.config.get("DISTRIBUTED_STORAGE_PREFERENCE", None)
        if not preference:
            preference = list(storages.keys())

        default_locations = app.config.get("DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS") or []

        download_proxy = None
        if app.config.get("FEATURE_PROXY_STORAGE", False) and instance_keys is not None:
            download_proxy = DownloadProxy(app, instance_keys)

        d_storage = DistributedStorage(
            storages,
            preference,
            default_locations,
            download_proxy,
            app.config.get("REGISTRY_STATE") == "readonly",
        )

        # register extension with app
        app.extensions = getattr(app, "extensions", {})
        app.extensions["storage"] = d_storage
        return d_storage

    def __getattr__(self, name):
        return getattr(self.state, name, None)
