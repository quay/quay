from typing import Dict, Union
import json
import tarfile

from abc import ABCMeta, abstractmethod
from collections import namedtuple
from io import BytesIO
from enum import Enum, unique
from six import add_metaclass

from image.docker.schema2 import EMPTY_LAYER_BYTES

Image = namedtuple(
    "Image", ["id", "parent_id", "bytes", "size", "config", "created", "urls", "is_empty"]
)
Image.__new__.__defaults__ = (None, None, None, None, False)

PushResult = namedtuple("PushResult", ["manifests", "headers"])
PullResult = namedtuple("PullResult", ["manifests", "image_ids"])


def layer_bytes_for_contents(contents, mode="|gz", other_files=None, empty=False):
    if empty:
        return EMPTY_LAYER_BYTES

    layer_data = BytesIO()
    tar_file = tarfile.open(fileobj=layer_data, mode="w" + mode)

    def add_file(name, contents):
        tar_file_info = tarfile.TarInfo(name=name)
        tar_file_info.type = tarfile.REGTYPE
        tar_file_info.size = len(contents)
        tar_file_info.mtime = 1

        tar_file.addfile(tar_file_info, BytesIO(contents))

    add_file("contents", contents)

    if other_files is not None:
        for file_name, file_contents in other_files.items():
            add_file(file_name, file_contents)

    tar_file.close()

    layer_bytes = layer_data.getvalue()
    layer_data.close()
    return layer_bytes


@unique
class Failures(Enum):
    """
    Defines the various forms of expected failure.
    """

    UNAUTHENTICATED = "unauthenticated"
    UNAUTHORIZED = "unauthorized"
    INVALID_AUTHENTICATION = "invalid-authentication"
    INVALID_REGISTRY = "invalid-registry"
    INVALID_REPOSITORY = "invalid-repository"
    SLASH_REPOSITORY = "slash-repository"
    APP_REPOSITORY = "app-repository"
    UNKNOWN_TAG = "unknown-tag"
    ANONYMOUS_NOT_ALLOWED = "anonymous-not-allowed"
    DISALLOWED_LIBRARY_NAMESPACE = "disallowed-library-namespace"
    MISSING_TAG = "missing-tag"
    INVALID_TAG = "invalid-tag"
    INVALID_MANIFEST = "invalid-manifest"
    INVALID_MANIFEST_IN_LIST = "invalid-manifest-in-list"
    INVALID_IMAGES = "invalid-images"
    UNSUPPORTED_CONTENT_TYPE = "unsupported-content-type"
    INVALID_BLOB = "invalid-blob"
    NAMESPACE_DISABLED = "namespace-disabled"
    UNAUTHORIZED_FOR_MOUNT = "unauthorized-for-mount"
    GEO_BLOCKED = "geo-blocked"
    READ_ONLY = "read-only"
    MIRROR_ONLY = "mirror-only"
    MIRROR_MISCONFIGURED = "mirror-misconfigured"
    MIRROR_ROBOT_MISSING = "mirror-robot-missing"
    READONLY_REGISTRY = "readonly-registry"


class ProtocolOptions(object):
    def __init__(self):
        self.scopes = None
        self.cancel_blob_upload = False
        self.manifest_invalid_blob_references = False
        self.chunks_for_upload = None
        self.skip_head_checks = False
        self.manifest_content_type = None
        self.accept_mimetypes = None
        self.mount_blobs = None
        self.push_by_manifest_digest = False
        self.request_addr = None
        self.skip_blob_push_checks = False
        self.ensure_ascii = True
        self.attempt_pull_without_token = False
        self.with_broken_manifest_config = False
        self.require_matching_manifest_type = False


@add_metaclass(ABCMeta)
class RegistryProtocol(object):
    """
    Interface for protocols.
    """

    FAILURE_CODES = {}  # type: Dict[Union[V1ProtocolSteps,V2ProtocolSteps], Dict[Failures, int]]

    @abstractmethod
    def login(self, session, username, password, scopes, expect_success):
        """
        Performs the login flow with the given credentials, over the given scopes.
        """

    @abstractmethod
    def pull(
        self,
        session,
        namespace,
        repo_name,
        tag_names,
        images,
        credentials=None,
        expected_failure=None,
        options=None,
    ):
        """
        Pulls the given tag via the given session, using the given credentials, and ensures the
        given images match.
        """

    @abstractmethod
    def push(
        self,
        session,
        namespace,
        repo_name,
        tag_names,
        images,
        credentials=None,
        expected_failure=None,
        options=None,
    ):
        """
        Pushes the specified images as the given tag via the given session, using the given
        credentials.
        """

    @abstractmethod
    def delete(
        self,
        session,
        namespace,
        repo_name,
        tag_names,
        credentials=None,
        expected_failure=None,
        options=None,
    ):
        """
        Deletes some tags.
        """

    def repo_name(self, namespace, repo_name):
        if namespace:
            return "%s/%s" % (namespace, repo_name)

        return repo_name

    def conduct(
        self,
        session,
        method,
        url,
        expected_status=200,
        params=None,
        data=None,
        json_data=None,
        headers=None,
        auth=None,
        options=None,
    ):
        if json_data is not None:
            data = json.dumps(json_data).encode("utf-8")
            headers = headers or {}
            headers["Content-Type"] = "application/json"

        if options and options.request_addr:
            headers = headers or {}
            headers["X-Override-Remote-Addr-For-Testing"] = options.request_addr

        if isinstance(expected_status, tuple):
            expected_status, expected_failure, protocol_step = expected_status
            if expected_failure is not None:
                failures = self.__class__.FAILURE_CODES.get(protocol_step, {})
                expected_status = failures.get(expected_failure, expected_status)

        result = session.request(method, url, params=params, data=data, headers=headers, auth=auth)
        msg = "Expected response %s, got %s: %s" % (
            expected_status,
            result.status_code,
            result.text,
        )
        assert result.status_code == expected_status, msg
        return result
