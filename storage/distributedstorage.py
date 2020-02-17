import random
import logging

from functools import wraps

from storage.basestorage import StoragePaths, BaseStorage, BaseStorageV2

logger = logging.getLogger(__name__)


def _location_aware(unbound_func, requires_write=False):
    @wraps(unbound_func)
    def wrapper(self, locations, *args, **kwargs):
        if requires_write:
            assert not self.readonly_mode

        storage = None
        for preferred in self.preferred_locations:
            if preferred in locations:
                storage = self._storages[preferred]
                break

        if not storage:
            storage = self._storages[random.sample(locations, 1)[0]]

        storage_func = getattr(storage, unbound_func.__name__)
        return storage_func(*args, **kwargs)

    return wrapper


class DistributedStorage(StoragePaths):
    def __init__(
        self,
        storages,
        preferred_locations=None,
        default_locations=None,
        proxy=None,
        readonly_mode=False,
    ):
        self._storages = dict(storages)
        self.preferred_locations = list(preferred_locations or [])
        self.default_locations = list(default_locations or [])
        self.proxy = proxy
        self.readonly_mode = readonly_mode

    @property
    def locations(self):
        """
        Returns the names of the locations supported.
        """
        return list(self._storages.keys())

    _get_direct_download_url = _location_aware(BaseStorage.get_direct_download_url)

    get_direct_upload_url = _location_aware(BaseStorage.get_direct_upload_url)
    get_content = _location_aware(BaseStorage.get_content)
    put_content = _location_aware(BaseStorage.put_content, requires_write=True)
    stream_read = _location_aware(BaseStorage.stream_read)
    stream_read_file = _location_aware(BaseStorage.stream_read_file)
    stream_write = _location_aware(BaseStorage.stream_write, requires_write=True)
    exists = _location_aware(BaseStorage.exists)
    remove = _location_aware(BaseStorage.remove, requires_write=True)
    validate = _location_aware(BaseStorage.validate, requires_write=True)
    get_checksum = _location_aware(BaseStorage.get_checksum)
    get_supports_resumable_downloads = _location_aware(BaseStorage.get_supports_resumable_downloads)

    initiate_chunked_upload = _location_aware(
        BaseStorageV2.initiate_chunked_upload, requires_write=True
    )
    stream_upload_chunk = _location_aware(BaseStorageV2.stream_upload_chunk, requires_write=True)
    complete_chunked_upload = _location_aware(
        BaseStorageV2.complete_chunked_upload, requires_write=True
    )
    cancel_chunked_upload = _location_aware(
        BaseStorageV2.cancel_chunked_upload, requires_write=True
    )

    def get_direct_download_url(
        self, locations, path, request_ip=None, expires_in=600, requires_cors=False, head=False
    ):
        download_url = self._get_direct_download_url(
            locations, path, request_ip, expires_in, requires_cors, head
        )
        if download_url is None:
            return None

        if self.proxy is None:
            return download_url

        return self.proxy.proxy_download_url(download_url)

    def copy_between(self, path, source_location, destination_location):
        """
        Copies a file between the source location and the destination location.
        """
        source_storage = self._storages[source_location]
        destination_storage = self._storages[destination_location]
        source_storage.copy_to(destination_storage, path)
