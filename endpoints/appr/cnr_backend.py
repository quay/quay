import base64
import io
import tarfile
import gzip
import hashlib
import os
import threading


from cnr.exception import raise_package_not_found
from cnr.models.blob_base import BlobBase
from cnr.models.channel_base import ChannelBase
from cnr.models.db_base import CnrDB
from cnr.models.package_base import PackageBase, manifest_media_type

from flask import request
from app import storage
from digest.digest_tools import Digest, InvalidDigestException
from endpoints.appr.models_cnr import model
from util.request import get_request_ip


# NOTE: This is a copy of the Package class from the CNR implementation, modified to lazy
# load the tar contents and BytesIO so that we can avoid doing so in common GET operations
# such as simply retrieving Blob's.
class LazyPackage(object):
    def __init__(self, blob=None, b64_encoded=True):
        self.files = {}
        self.tar = None
        self.blob = None
        self._io_file = None
        self._digest = None
        self._size = None
        self.b64blob = None
        if blob is not None:
            self.load(blob, b64_encoded)

        self.lock = threading.RLock()

    def _load_blob(self, blob, b64_encoded):
        if b64_encoded:
            self.b64blob = blob
            self.blob = base64.b64decode(blob)
        else:
            self.b64blob = base64.b64encode(blob)
            self.blob = blob

    def load(self, blob, b64_encoded=True):
        self._digest = None
        self._load_blob(blob, b64_encoded)

    @property
    def io_file(self):
        self._lazy_load_file()
        return self._io_file

    def _lazy_load_file(self):
        with self.lock:
            if self._io_file is not None:
                return

            self._io_file = io.BytesIO(self.blob)

    def _lazy_load_tar(self):
        with self.lock:
            if self.tar is not None:
                return

            self.tar = tarfile.open(fileobj=self.io_file, mode="r:gz")
            for member in self.tar.getmembers():
                tfile = self.tar.extractfile(member)
                if tfile is not None:
                    self.files[tfile.name] = tfile.read()

    def extract(self, dest):
        self._lazy_load_tar()
        self.tar.extractall(dest)

    def pack(self, dest):
        with open(dest, "wb") as destfile:
            destfile.write(self.blob)

    def tree(self, directory=None):
        self._lazy_load_tar()
        files = self.files.keys()
        files.sort()
        if directory is not None:
            filtered = [x for x in files if x.startswith(directory)]
        else:
            filtered = files
        return filtered

    def file(self, filename):
        self._lazy_load_tar()
        return self.files[filename]

    @property
    def size(self):
        self._lazy_load_file()
        if self._size is None:
            self.io_file.seek(0, os.SEEK_END)
            self._size = self.io_file.tell()
        return self._size

    @property
    def digest(self):
        self._lazy_load_file()
        if self._digest is None:
            self.io_file.seek(0)
            gunzip = gzip.GzipFile(fileobj=self.io_file, mode="r").read()
            self._digest = hashlib.sha256(gunzip).hexdigest()
            self.io_file.seek(0)
        return self._digest


class Blob(BlobBase):
    def __init__(self, package_name, blob, b64_encoded=True):
        self.package = package_name
        self.packager = LazyPackage(blob, b64_encoded)

    @classmethod
    def upload_url(cls, digest):
        # Ensure we have a valid digest.
        try:
            Digest.parse_digest("sha256:%s" % digest)
        except InvalidDigestException:
            return None

        return "cnr/blobs/sha256/%s/%s" % (digest[0:2], digest)

    def save(self, content_media_type):
        model.store_blob(self, content_media_type)

    @classmethod
    def delete(cls, package_name, digest):
        pass

    @classmethod
    def _fetch_b64blob(cls, package_name, digest):
        blobpath = cls.upload_url(digest)
        if blobpath is None:
            raise_package_not_found(package_name, digest)

        locations = model.get_blob_locations(digest)
        if not locations:
            raise_package_not_found(package_name, digest)
        return base64.b64encode(storage.get_content(locations, blobpath))

    @classmethod
    def download_url(cls, package_name, digest):
        blobpath = cls.upload_url(digest)
        if blobpath is None:
            raise_package_not_found(package_name, digest)

        locations = model.get_blob_locations(digest)
        if not locations:
            raise_package_not_found(package_name, digest)
        return storage.get_direct_download_url(locations, blobpath, get_request_ip())


class Channel(ChannelBase):
    """
    CNR Channel model implemented against the Quay data model.
    """

    def __init__(self, name, package, current=None):
        super(Channel, self).__init__(name, package, current=current)
        self._channel_data = None

    def _exists(self):
        """
        Check if the channel is saved already.
        """
        return model.channel_exists(self.package, self.name)

    @classmethod
    def get(cls, name, package):
        chanview = model.fetch_channel(package, name, with_releases=False)
        return cls(name, package, chanview.current)

    def save(self):
        model.update_channel(self.package, self.name, self.current)

    def delete(self):
        model.delete_channel(self.package, self.name)

    @classmethod
    def all(cls, package_name):
        return [Channel(c.name, package_name, c.current) for c in model.list_channels(package_name)]

    @property
    def _channel(self):
        if self._channel_data is None:
            self._channel_data = model.fetch_channel(self.package, self.name)
        return self._channel_data

    def releases(self):
        """
        Returns the list of versions.
        """
        return self._channel.releases

    def _add_release(self, release):
        return model.update_channel(self.package, self.name, release)._asdict

    def _remove_release(self, release):
        model.delete_channel(self.package, self.name)


class User(object):
    """
    User in CNR models.
    """

    @classmethod
    def get_user(cls, username, password):
        """
        Returns True if user creds is valid.
        """
        return model.get_user(username, password)


class Package(PackageBase):
    """
    CNR Package model implemented against the Quay data model.
    """

    @classmethod
    def _apptuple_to_dict(cls, apptuple):
        return {
            "release": apptuple.release,
            "created_at": apptuple.created_at,
            "digest": apptuple.manifest.digest,
            "mediaType": apptuple.manifest.mediaType,
            "package": apptuple.name,
            "content": apptuple.manifest.content._asdict(),
        }

    @classmethod
    def create_repository(cls, package_name, visibility, owner):
        model.create_application(package_name, visibility, owner)

    @classmethod
    def exists(cls, package_name):
        return model.application_exists(package_name)

    @classmethod
    def all(cls, organization=None, media_type=None, search=None, username=None, **kwargs):
        return [
            dict(x._asdict())
            for x in model.list_applications(
                namespace=organization, media_type=media_type, search=search, username=username
            )
        ]

    @classmethod
    def _fetch(cls, package_name, release, media_type):
        data = model.fetch_release(package_name, release, manifest_media_type(media_type))
        return cls._apptuple_to_dict(data)

    @classmethod
    def all_releases(cls, package_name, media_type=None):
        return model.list_releases(package_name, media_type)

    @classmethod
    def search(cls, query, username=None):
        return model.basic_search(query, username=username)

    def _save(self, force=False, **kwargs):
        user = kwargs["user"]
        visibility = kwargs["visibility"]
        model.create_release(self, user, visibility, force)

    @classmethod
    def _delete(cls, package_name, release, media_type):
        model.delete_release(package_name, release, manifest_media_type(media_type))

    @classmethod
    def isdeleted_release(cls, package, release):
        return model.release_exists(package, release)

    def channels(self, channel_class, iscurrent=True):
        return [
            c.name
            for c in model.list_release_channels(self.package, self.release, active=iscurrent)
        ]

    @classmethod
    def manifests(cls, package, release=None):
        return model.list_manifests(package, release)

    @classmethod
    def dump_all(cls, blob_cls):
        raise NotImplementedError


class QuayDB(CnrDB):
    """
    Wrapper Class to embed all CNR Models.
    """

    Channel = Channel
    Package = Package
    Blob = Blob

    @classmethod
    def reset_db(cls, force=False):
        pass
