import logging
import requests
import json
import os

from collections import namedtuple
from enum import Enum

from abc import ABCMeta, abstractmethod
from six import add_metaclass
from urlparse import urljoin
from jsonschema import validate, RefResolver

from data.registry_model.datatypes import Manifest as ManifestDataType
from data.model.storage import get_storage_locations


logger = logging.getLogger(__name__)


class Non200ResponseException(Exception):
    """
    Exception raised when the upstream API returns a non-200 HTTP status code.
    """

    def __init__(self, response):
        super(Non200ResponseException, self).__init__()
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


Action = namedtuple("Action", ["name", "payload"])

actions = {
    "State": lambda: Action("State", ("GET", "state", None)),
    "Index": lambda manifest: Action("Index", ("POST", "index_report", manifest)),
    "GetIndexReport": lambda manifest_hash: Action(
        "GetIndexReport", ("GET", "index_report/" + manifest_hash, None)
    ),
    "GetVulnerabilityReport": lambda manifest_hash: Action(
        "GetVulnerabilityReport", ("GET", "vulnerability_report/" + manifest_hash, None,)
    ),
}


class ClairSecurityScannerAPI(SecurityScannerAPIInterface):
    def __init__(self, endpoint, client, storage):
        self._client = client
        self._storage = storage
        self.secscan_api_endpoint = urljoin(endpoint, "/api/v1/")

    def state(self):
        try:
            resp = self._perform(actions["State"]())
        except (Non200ResponseException, IncompatibleAPIResponse) as ex:
            raise APIRequestFailure(ex.message)

        return resp.json()

    def index(self, manifest, layers):
        # TODO: Better method of determining if a manifest can be indexed (new field or content-type whitelist)
        assert isinstance(manifest, ManifestDataType) and not manifest.is_manifest_list

        uri_for = lambda layer: self._storage.get_direct_download_url(
            self._storage.locations, layer.blob.storage_path
        )
        body = {
            "hash": manifest.digest,
            "layers": [
                {
                    "hash": str(l.layer_info.blob_digest),
                    "uri": uri_for(l),
                    "headers": {"Accept": ["application/gzip"],},
                }
                for l in layers
            ],
        }

        try:
            resp = self._perform(actions["Index"](body))
        except (Non200ResponseException, IncompatibleAPIResponse) as ex:
            raise APIRequestFailure(ex.message)

        return (resp.json(), resp.headers["etag"])

    def index_report(self, manifest_hash):
        try:
            resp = self._perform(actions["GetIndexReport"](manifest_hash))
        except IncompatibleAPIResponse as ex:
            raise APIRequestFailure(ex.message)
        except Non200ResponseException as ex:
            if ex.response.status_code == 404:
                return None
            raise APIRequestFailure(ex.message)

        return resp.json()

    def vulnerability_report(self, manifest_hash):
        try:
            resp = self._perform(actions["GetVulnerabilityReport"](manifest_hash))
        except IncompatibleAPIResponse as ex:
            raise APIRequestFailure(ex.message)
        except Non200ResponseException as ex:
            if ex.response.status_code == 404:
                return None
            raise APIRequestFailure(ex.message)

        return resp.json()

    def _perform(self, action):
        (method, path, body) = action.payload
        url = urljoin(self.secscan_api_endpoint, path)

        logger.debug("%sing security URL %s", method.upper(), url)
        try:
            resp = self._client.request(method, url, json=body)
        except requests.exceptions.ConnectionError as ce:
            logger.exception("Connection error when trying to connect to security scanner endpoint")
            msg = (
                "Connection error when trying to connect to security scanner endpoint: %s"
                % ce.message
            )
            raise APIRequestFailure(msg)

        if resp.status_code // 100 != 2:
            msg = (
                "Security scanner endpoint responded with non-200 HTTP status code: %s"
                % resp.status_code
            )
            logger.exception(msg)
            raise Non200ResponseException(resp)

        if not is_valid_response(action, resp.json()):
            msg = "Received incompatible response from security scanner"
            logger.exception(msg)
            raise IncompatibleAPIResponse(msg)

        return resp


def is_valid_response(action, resp={}):
    assert action.name in actions.keys()

    schema_for = {
        "State": "State",
        "Index": "IndexReport",
        "GetIndexReport": "IndexReport",
        "GetVulnerabilityReport": "VulnerabilityReport",
    }
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clair-v4.openapi.json")

    with open(filename) as openapi_file:
        openapi = json.load(openapi_file)
        resolver = RefResolver(base_uri="", referrer=openapi)
        schema = openapi["components"]["schemas"][schema_for[action.name]]

        try:
            validate(resp, schema, resolver=resolver)
            return True
        except Exception:
            return False
