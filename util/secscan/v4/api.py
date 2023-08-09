import base64
import functools
import json
import logging
import os
import re
import time
from abc import ABCMeta, abstractmethod
from collections import namedtuple
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict
from urllib.parse import urljoin

import jwt
import requests
from jsonschema import RefResolver, validate
from six import add_metaclass

from data.registry_model.datatypes import Manifest as ManifestDataType
from util.metrics.prometheus import secscan_index_layer_size, secscan_request_duration

logger = logging.getLogger(__name__)

DOWNLOAD_VALIDITY_LIFETIME_S = 60  # Amount of time the security scanner has to call the layer URL
INDEX_REQUEST_TIMEOUT = 600


class Non200ResponseException(Exception):
    """
    Exception raised when the upstream API returns a non-200 HTTP status code.
    """

    def __init__(self, response):
        super(Non200ResponseException, self).__init__()
        self.response = response


class BadRequestResponseException(Exception):
    """
    Exception raised when the upstream API returns a non-200 HTTP status code.
    """

    def __init__(self, response):
        super(BadRequestResponseException, self).__init__()
        self.response = response


class IncompatibleAPIResponse(Exception):
    """
    Exception raised when upstream API returns a response which does not match
    the expected schema.
    """


class APIRequestFailure(Exception):
    """
    Exception raised when there is a failure to conduct an API request.
    """


class InvalidContentSent(Exception):
    """
    Exception raised when malformed content is sent to API.
    """


class LayerTooLargeException(Exception):
    """
    Exception raised when layer above configured max.
    """


@add_metaclass(ABCMeta)
class SecurityScannerAPIInterface(object):
    @abstractmethod
    def state(self):
        """
        The state endpoint returns a json structure indicating the indexer's internal configuration state.
        A client may be interested in this as a signal that manifests may need to be re-indexed.
        """
        pass

    @abstractmethod
    def index(self, manifest, layers):
        """
        By submitting a Manifest object to this endpoint Clair will fetch the layers,
        scan each layer's contents, and provide an index of discovered packages, repository and distribution information.
        Returns a tuple of the `IndexReport` and the indexer state.
        """
        pass

    @abstractmethod
    def index_report(self, manifest_hash):
        """
        Given a Manifest's content addressable hash an `IndexReport` will be retrieved if exists.
        """
        pass

    @abstractmethod
    def vulnerability_report(self, manifest_hash):
        """
        Given a Manifest's content addressable hash a `VulnerabilityReport` will be created.
        The Manifest must have been Indexed first via the Index endpoint.
        """
        pass

    @abstractmethod
    def retrieve_notification_page(self, notification_id, next_param=None):
        """
        Retrieves a page of results from a notification.
        """
        pass


Action = namedtuple("Action", ["name", "payload"])

actions: Dict[str, Callable[..., Action]] = {
    "IndexState": lambda: Action("IndexState", ("GET", "/indexer/api/v1/index_state", None)),
    "Index": lambda manifest: Action("Index", ("POST", "/indexer/api/v1/index_report", manifest)),
    "GetIndexReport": lambda manifest_hash: Action(
        "GetIndexReport", ("GET", "/indexer/api/v1/index_report/" + manifest_hash, None)
    ),
    "GetVulnerabilityReport": lambda manifest_hash: Action(
        "GetVulnerabilityReport",
        (
            "GET",
            "/matcher/api/v1/vulnerability_report/" + manifest_hash,
            None,
        ),
    ),
    "DeleteNotification": lambda notification_id: Action(
        "DeleteNotification",
        (
            "DELETE",
            "/notifier/api/v1/notification/%s" % (notification_id),
            None,
        ),
    ),
    "GetNotification": lambda notification_id, next_param: Action(
        "GetNotification",
        (
            "GET",
            "/notifier/api/v1/notification/%s%s"
            % (notification_id, "?next=" + next_param if next_param else ""),
            None,
        ),
    ),
    "DeleteIndexReport": lambda manifest_hash: Action(
        "DeleteIndexReport",
        (
            "DELETE",
            "/indexer/api/v1/index_report/" + manifest_hash,
            None,
        ),
    ),
}


def _layer_size_str_to_bytes(layer_size: str) -> int:
    if not layer_size:
        return 0

    parsed_max_layer_size = re.split(r"(\d+)", layer_size)
    if len(parsed_max_layer_size) < 2:
        return 0

    units = {"B": 1, "K": 2**10, "M": 2**20, "G": 2**30, "T": 2**40}

    max_size, unit = parsed_max_layer_size[-2], parsed_max_layer_size[-1]

    msg = "invalid max layer size format. e.g 1M, 1G"
    assert max_size.isdigit() and unit.upper() in units.keys(), msg

    return int(max_size) * units[unit]


class ClairSecurityScannerAPI(SecurityScannerAPIInterface):
    """
    Class implements the SecurityScannerAPIInterface for Clair V4.

    If the jwt_psk value is not None, it must be a base64 encoded string.
    The base64 encoded string will be decoded and used to sign JWT(s) for all
    Clair V4 requests.
    """

    def __init__(self, endpoint, client, blob_url_retriever, jwt_psk=None, max_layer_size=None):
        self._client = client
        self._blob_url_retriever = blob_url_retriever
        self.jwt_psk = None
        self.max_layer_size = _layer_size_str_to_bytes(max_layer_size)

        if jwt_psk is not None:
            self.jwt_psk = base64.b64decode(jwt_psk)

        self.secscan_api_endpoint = endpoint

    def state(self):
        try:
            resp = self._perform(actions["IndexState"]())
        except (Non200ResponseException, IncompatibleAPIResponse) as ex:
            raise APIRequestFailure(ex)

        return resp.json()

    def index(self, manifest, layers):
        # TODO: Better method of determining if a manifest can be indexed (new field or content-type whitelist)
        assert isinstance(manifest, ManifestDataType) and not manifest.is_manifest_list

        def _join(first, second):
            first.update(second)
            return first

        body = {
            "hash": manifest.digest,
            "layers": [],
        }

        for l in layers:
            layer_compressed_size = l.layer_info.compressed_size
            if (
                self.max_layer_size
                and layer_compressed_size is not None
                and layer_compressed_size > self.max_layer_size
            ):
                raise LayerTooLargeException()

            secscan_index_layer_size.observe(layer_compressed_size or 0)

            body["layers"].append(
                {
                    "hash": str(l.layer_info.blob_digest),
                    "uri": self._blob_url_retriever.url_for_download(manifest.repository, l.blob)
                    if not l.layer_info.is_remote
                    else l.layer_info.urls[0],
                    "headers": _join(
                        {
                            "Accept": ["application/gzip"],
                        },
                        (
                            self._blob_url_retriever.headers_for_download(
                                manifest.repository, l.blob, DOWNLOAD_VALIDITY_LIFETIME_S
                            )
                            if not l.layer_info.is_remote
                            else {}
                        ),
                    ),
                }
            )

        try:
            resp = self._perform(actions["Index"](body))
        except BadRequestResponseException as ex:
            raise InvalidContentSent(ex)
        except (Non200ResponseException, IncompatibleAPIResponse) as ex:
            raise APIRequestFailure(ex)

        # Required clair indexer hash.
        # RFC for etag specifies surrounding double quotes, which need to be stripped (below)
        assert resp.headers["etag"]

        return (resp.json(), resp.headers["etag"].strip('"'))

    def delete(self, manifest_digest):
        try:
            resp = self._perform(actions["DeleteIndexReport"](manifest_digest))
        except BadRequestResponseException as ex:
            raise InvalidContentSent(ex)
        except (Non200ResponseException, IncompatibleAPIResponse) as ex:
            raise APIRequestFailure(ex)

        return resp.json()

    def retrieve_notification_page(self, notification_id, next_param=None):
        try:
            resp = self._perform(actions["GetNotification"](notification_id, next_param))
        except IncompatibleAPIResponse as ex:
            raise APIRequestFailure(ex)
        except Non200ResponseException as ex:
            if ex.response.status_code == 404:
                return None
            raise APIRequestFailure(ex)

        return resp.json()

    def delete_notification(self, notification_id):
        try:
            resp = self._perform(actions["DeleteNotification"](notification_id))
        except IncompatibleAPIResponse as ex:
            raise APIRequestFailure(ex)
        except Non200ResponseException as ex:
            if ex.response.status_code == 404:
                return

            raise APIRequestFailure(ex)

    def index_report(self, manifest_hash):
        try:
            resp = self._perform(actions["GetIndexReport"](manifest_hash))
        except IncompatibleAPIResponse as ex:
            raise APIRequestFailure(ex)
        except Non200ResponseException as ex:
            if ex.response.status_code == 404:
                return None
            raise APIRequestFailure(ex)

        return resp.json()

    def vulnerability_report(self, manifest_hash):
        try:
            resp = self._perform(actions["GetVulnerabilityReport"](manifest_hash))
        except IncompatibleAPIResponse as ex:
            raise APIRequestFailure(ex)
        except Non200ResponseException as ex:
            if ex.response.status_code == 404:
                return None
            raise APIRequestFailure(ex)

        return resp.json()

    def _perform(self, action):
        request_start_time = time.time()
        (method, path, body) = action.payload
        url = urljoin(self.secscan_api_endpoint, path)

        headers = {}
        if self.jwt_psk:
            token = self._sign_jwt()
            headers["authorization"] = "{} {}".format("Bearer", token)
            logger.debug("generated jwt for security scanner request")

        logger.debug("%sing security URL %s", method.upper(), url)
        try:
            resp = self._client.request(
                method, url, json=body, headers=headers, timeout=INDEX_REQUEST_TIMEOUT
            )
        except requests.exceptions.ConnectionError as ce:
            logger.exception("Connection error when trying to connect to security scanner endpoint")
            msg = "Connection error when trying to connect to security scanner endpoint: %s" % str(
                ce
            )
            raise APIRequestFailure(msg)

        dur = time.time() - request_start_time
        secscan_request_duration.labels(method, action.name, resp.status_code).observe(dur)

        if resp.status_code == 400:
            msg = (
                "Security scanner endpoint responded with 400 HTTP status code: %s"
                % resp.content.decode("ascii")
            )
            logger.exception(msg)
            raise BadRequestResponseException(resp)
        elif resp.status_code // 100 != 2:
            msg = (
                "Security scanner endpoint responded with non-200 HTTP status code: %s"
                % resp.status_code
            )
            logger.exception(msg)
            raise Non200ResponseException(resp)

        if not is_valid_response(action, resp):
            raise IncompatibleAPIResponse("Received incompatible response from security scanner")

        return resp

    def _sign_jwt(self):
        """
        Sign and return a jwt.

        If self.jwt_psk is provided a pre-shared key will be used as the signing key.
        """
        payload = {
            "iss": "quay",
            "exp": datetime.utcnow() + timedelta(minutes=5),
        }
        token = jwt.encode(payload, self.jwt_psk, algorithm="HS256")

        return token


def is_valid_response(action, resp):
    assert action.name in actions.keys()

    schema_for = {
        "IndexState": "State",
        "Index": "IndexReport",
        "GetIndexReport": "IndexReport",
        "GetVulnerabilityReport": "VulnerabilityReport",
        "GetNotification": "PagedNotifications",
        "DeleteNotification": None,
    }
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clair-v4.openapi.json")

    if schema_for[action.name] is None:
        return True

    with open(filename) as openapi_file:
        openapi = json.load(openapi_file)
        resolver = RefResolver(base_uri="", referrer=openapi)
        schema = openapi["components"]["schemas"][schema_for[action.name]]

        try:
            validate(resp.json(), schema, resolver=resolver)
            return True
        except Exception:
            logger.exception("Security scanner response failed OpenAPI validation")
            return False
