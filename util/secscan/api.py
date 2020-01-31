import os
import logging

from abc import ABCMeta, abstractmethod
from six import add_metaclass
from urllib.parse import urljoin

import requests

from data import model
from data.database import CloseForLongOperation, TagManifest, Image, Manifest, ManifestLegacyImage
from data.model.storage import get_storage_locations
from data.model.image import get_image_with_storage
from data.registry_model.datatypes import Manifest as ManifestDataType, LegacyImage
from util.abchelpers import nooper
from util.failover import failover, FailoverException
from util.secscan.validator import SecurityConfigValidator
from util.security.registry_jwt import generate_bearer_token, build_context_and_subject

from _init import CONF_DIR

TOKEN_VALIDITY_LIFETIME_S = 60  # Amount of time the security scanner has to call the layer URL

UNKNOWN_PARENT_LAYER_ERROR_MSG = "worker: parent layer is unknown, it must be processed first"

MITM_CERT_PATH = os.path.join(CONF_DIR, "mitm.cert")

DEFAULT_HTTP_HEADERS = {"Connection": "close"}

logger = logging.getLogger(__name__)


class AnalyzeLayerException(Exception):
    """
    Exception raised when a layer fails to analyze due to a request issue.
    """


class AnalyzeLayerRetryException(Exception):
    """
    Exception raised when a layer fails to analyze due to a request issue, and the request should be
    retried.
    """


class MissingParentLayerException(AnalyzeLayerException):
    """
    Exception raised when the parent of the layer is missing from the security scanner.
    """


class InvalidLayerException(AnalyzeLayerException):
    """
    Exception raised when the layer itself cannot be handled by the security scanner.
    """


class APIRequestFailure(Exception):
    """
    Exception raised when there is a failure to conduct an API request.
    """


class Non200ResponseException(Exception):
    """
    Exception raised when the upstream API returns a non-200 HTTP status code.
    """

    def __init__(self, response):
        super(Non200ResponseException, self).__init__()
        self.response = response


_API_METHOD_INSERT = "layers"
_API_METHOD_GET_LAYER = "layers/%s"
_API_METHOD_DELETE_LAYER = "layers/%s"
_API_METHOD_MARK_NOTIFICATION_READ = "notifications/%s"
_API_METHOD_GET_NOTIFICATION = "notifications/%s"
_API_METHOD_PING = "metrics"


def compute_layer_id(layer):
    """
    Returns the ID for the layer in the security scanner.
    """
    # NOTE: this is temporary until we switch to Clair V3.
    if isinstance(layer, ManifestDataType):
        if layer._is_tag_manifest:
            layer = TagManifest.get(id=layer._db_id).tag.image
        else:
            manifest = Manifest.get(id=layer._db_id)
            try:
                layer = ManifestLegacyImage.get(manifest=manifest).image
            except ManifestLegacyImage.DoesNotExist:
                return None
    elif isinstance(layer, LegacyImage):
        layer = Image.get(id=layer._db_id)

    assert layer.docker_image_id
    assert layer.storage.uuid
    return "%s.%s" % (layer.docker_image_id, layer.storage.uuid)


class SecurityScannerAPI(object):
    """
    Helper class for talking to the Security Scan service (usually Clair).
    """

    def __init__(
        self,
        config,
        storage,
        server_hostname=None,
        client=None,
        skip_validation=False,
        uri_creator=None,
        instance_keys=None,
    ):
        feature_enabled = config.get("FEATURE_SECURITY_SCANNER", False)
        has_valid_config = skip_validation

        if not skip_validation and feature_enabled:
            config_validator = SecurityConfigValidator(
                feature_enabled, config.get("SECURITY_SCANNER_ENDPOINT")
            )
            has_valid_config = config_validator.valid()

        if feature_enabled and has_valid_config:
            self.state = ImplementedSecurityScannerAPI(
                config,
                storage,
                server_hostname,
                client=client,
                uri_creator=uri_creator,
                instance_keys=instance_keys,
            )
        else:
            self.state = NoopSecurityScannerAPI()

    def __getattr__(self, name):
        return getattr(self.state, name, None)


@add_metaclass(ABCMeta)
class SecurityScannerAPIInterface(object):
    """
    Helper class for talking to the Security Scan service (usually Clair).
    """

    @abstractmethod
    def cleanup_layers(self, layers):
        """
        Callback invoked by garbage collection to cleanup any layers that no longer need to be
        stored in the security scanner.
        """
        pass

    @abstractmethod
    def ping(self):
        """
        Calls GET on the metrics endpoint of the security scanner to ensure it is running and
        properly configured.

        Returns the HTTP response.
        """
        pass

    @abstractmethod
    def delete_layer(self, layer):
        """
        Calls DELETE on the given layer in the security scanner, removing it from its database.
        """
        pass

    @abstractmethod
    def analyze_layer(self, layer):
        """
        Posts the given layer to the security scanner for analysis, blocking until complete.

        Returns the analysis version on success or raises an exception deriving from
        AnalyzeLayerException on failure. Callers should handle all cases of AnalyzeLayerException.
        """
        pass

    @abstractmethod
    def check_layer_vulnerable(self, layer_id, cve_name):
        """
        Checks to see if the layer with the given ID is vulnerable to the specified CVE.
        """
        pass

    @abstractmethod
    def get_notification(self, notification_name, layer_limit=100, page=None):
        """
        Gets the data for a specific notification, with optional page token.

        Returns a tuple of the data (None on failure) and whether to retry.
        """
        pass

    @abstractmethod
    def mark_notification_read(self, notification_name):
        """
        Marks a security scanner notification as read.
        """
        pass

    @abstractmethod
    def get_layer_data(self, layer, include_features=False, include_vulnerabilities=False):
        """
        Returns the layer data for the specified layer.

        On error, returns None.
        """
        pass


@nooper
class NoopSecurityScannerAPI(SecurityScannerAPIInterface):
    """
    No-op version of the security scanner API.
    """

    pass


class ImplementedSecurityScannerAPI(SecurityScannerAPIInterface):
    """
    Helper class for talking to the Security Scan service (Clair).
    """

    # TODO refactor this to not take an app config, and instead just the things it needs as a config object
    def __init__(
        self, config, storage, server_hostname, client=None, uri_creator=None, instance_keys=None
    ):
        self._config = config
        self._instance_keys = instance_keys
        self._client = client
        self._storage = storage
        self._server_hostname = server_hostname
        self._default_storage_locations = config["DISTRIBUTED_STORAGE_PREFERENCE"]
        self._target_version = config.get("SECURITY_SCANNER_ENGINE_VERSION_TARGET", 2)
        self._uri_creator = uri_creator

    def _get_image_url_and_auth(self, image):
        """
        Returns a tuple of the url and the auth header value that must be used to fetch the layer
        data itself.

        If the image can't be addressed, we return None.
        """
        if self._instance_keys is None:
            raise Exception("No Instance keys provided to Security Scanner API")

        path = model.storage.get_layer_path(image.storage)
        locations = self._default_storage_locations

        if not self._storage.exists(locations, path):
            locations = get_storage_locations(image.storage.uuid)
            if not locations or not self._storage.exists(locations, path):
                logger.warning(
                    "Could not find a valid location to download layer %s out of %s",
                    compute_layer_id(image),
                    locations,
                )
                return None, None

        uri = self._storage.get_direct_download_url(locations, path)
        auth_header = None
        if uri is None:
            # Use the registry API instead, with a signed JWT giving access
            repo_name = image.repository.name
            namespace_name = image.repository.namespace_user.username
            repository_and_namespace = "/".join([namespace_name, repo_name])

            # Generate the JWT which will authorize this
            audience = self._server_hostname
            context, subject = build_context_and_subject()
            access = [
                {"type": "repository", "name": repository_and_namespace, "actions": ["pull"],}
            ]

            auth_token = generate_bearer_token(
                audience, subject, context, access, TOKEN_VALIDITY_LIFETIME_S, self._instance_keys
            )
            auth_header = "Bearer " + auth_token.decode("ascii")

            uri = self._uri_creator(repository_and_namespace, image.storage.content_checksum)

        return uri, auth_header

    def _new_analyze_request(self, layer):
        """
        Create the request body to submit the given layer for analysis.

        If the layer's URL cannot be found, returns None.
        """
        layer_id = compute_layer_id(layer)
        if layer_id is None:
            return None

        url, auth_header = self._get_image_url_and_auth(layer)
        if url is None:
            return None

        layer_request = {
            "Name": layer_id,
            "Path": url,
            "Format": "Docker",
        }

        if auth_header is not None:
            layer_request["Headers"] = {
                "Authorization": auth_header,
            }

        if layer.parent is not None:
            if layer.parent.docker_image_id and layer.parent.storage.uuid:
                layer_request["ParentName"] = compute_layer_id(layer.parent)

        return {
            "Layer": layer_request,
        }

    def cleanup_layers(self, layers):
        """
        Callback invoked by garbage collection to cleanup any layers that no longer need to be
        stored in the security scanner.
        """
        for layer in layers:
            self.delete_layer(layer)

    def ping(self):
        """
        Calls GET on the metrics endpoint of the security scanner to ensure it is running and
        properly configured.

        Returns the HTTP response.
        """
        try:
            return self._call("GET", _API_METHOD_PING)
        except requests.exceptions.Timeout as tie:
            logger.exception("Timeout when trying to connect to security scanner endpoint")
            msg = "Timeout when trying to connect to security scanner endpoint: %s" % tie.message
            raise Exception(msg)
        except requests.exceptions.ConnectionError as ce:
            logger.exception("Connection error when trying to connect to security scanner endpoint")
            msg = (
                "Connection error when trying to connect to security scanner endpoint: %s"
                % ce.message
            )
            raise Exception(msg)
        except (requests.exceptions.RequestException, ValueError) as ve:
            logger.exception("Exception when trying to connect to security scanner endpoint")
            msg = "Exception when trying to connect to security scanner endpoint: %s" % ve
            raise Exception(msg)

    def delete_layer(self, layer):
        """
        Calls DELETE on the given layer in the security scanner, removing it from its database.
        """
        layer_id = compute_layer_id(layer)
        if layer_id is None:
            return None

        # NOTE: We are adding an extra check here for the time being just to be sure we're
        # not hitting any overlap.
        docker_image_id, layer_storage_uuid = layer_id.split(".")
        if get_image_with_storage(docker_image_id, layer_storage_uuid):
            logger.warning("Found shared Docker ID and storage for layer %s", layer_id)
            return False

        try:
            self._call("DELETE", _API_METHOD_DELETE_LAYER % layer_id)
            return True
        except Non200ResponseException:
            return False
        except requests.exceptions.RequestException:
            logger.exception("Failed to delete layer: %s", layer_id)
            return False

    def analyze_layer(self, layer):
        """
        Posts the given layer to the security scanner for analysis, blocking until complete.

        Returns the analysis version on success or raises an exception deriving from
        AnalyzeLayerException on failure. Callers should handle all cases of AnalyzeLayerException.
        """

        def _response_json(request, response):
            try:
                return response.json()
            except ValueError:
                logger.exception(
                    "Failed to decode JSON when analyzing layer %s", request["Layer"]["Name"]
                )
                raise AnalyzeLayerException

        request = self._new_analyze_request(layer)
        if not request:
            logger.error("Could not build analyze request for layer %s", layer.id)
            raise AnalyzeLayerException

        logger.info("Analyzing layer %s", request["Layer"]["Name"])
        try:
            response = self._call("POST", _API_METHOD_INSERT, body=request)
        except requests.exceptions.Timeout:
            logger.exception("Timeout when trying to post layer data response for %s", layer.id)
            raise AnalyzeLayerRetryException
        except requests.exceptions.ConnectionError:
            logger.exception(
                "Connection error when trying to post layer data response for %s", layer.id
            )
            raise AnalyzeLayerRetryException
        except (requests.exceptions.RequestException) as re:
            logger.exception("Failed to post layer data response for %s: %s", layer.id, re)
            raise AnalyzeLayerException
        except Non200ResponseException as ex:
            message = _response_json(request, ex.response).get("Error").get("Message", "")
            logger.warning(
                "A warning event occurred when analyzing layer %s (status code %s): %s",
                request["Layer"]["Name"],
                ex.response.status_code,
                message,
            )
            # 400 means the layer could not be analyzed due to a bad request.
            if ex.response.status_code == 400:
                if message == UNKNOWN_PARENT_LAYER_ERROR_MSG:
                    raise MissingParentLayerException(
                        "Bad request to security scanner: %s" % message
                    )
                else:
                    logger.exception("Got non-200 response for analyze of layer %s", layer.id)
                    raise AnalyzeLayerException("Bad request to security scanner: %s" % message)
            # 422 means that the layer could not be analyzed:
            # - the layer could not be extracted (might be a manifest or an invalid .tar.gz)
            # - the layer operating system / package manager is unsupported
            elif ex.response.status_code == 422:
                raise InvalidLayerException

            # Otherwise, it is some other error and we should retry.
            raise AnalyzeLayerRetryException

        # Return the parsed API version.
        return _response_json(request, response)["Layer"]["IndexedByVersion"]

    def check_layer_vulnerable(self, layer_id, cve_name):
        """
        Checks to see if the layer with the given ID is vulnerable to the specified CVE.
        """
        layer_data = self._get_layer_data(layer_id, include_vulnerabilities=True)
        if layer_data is None or "Layer" not in layer_data or "Features" not in layer_data["Layer"]:
            return False

        for feature in layer_data["Layer"]["Features"]:
            for vuln in feature.get("Vulnerabilities", []):
                if vuln["Name"] == cve_name:
                    return True

        return False

    def get_notification(self, notification_name, layer_limit=100, page=None):
        """
        Gets the data for a specific notification, with optional page token.

        Returns a tuple of the data (None on failure) and whether to retry.
        """
        try:
            params = {"limit": layer_limit}

            if page is not None:
                params["page"] = page

            response = self._call(
                "GET", _API_METHOD_GET_NOTIFICATION % notification_name, params=params
            )
            json_response = response.json()
        except requests.exceptions.Timeout:
            logger.exception("Timeout when trying to get notification for %s", notification_name)
            return None, True
        except requests.exceptions.ConnectionError:
            logger.exception(
                "Connection error when trying to get notification for %s", notification_name
            )
            return None, True
        except (requests.exceptions.RequestException, ValueError):
            logger.exception("Failed to get notification for %s", notification_name)
            return None, False
        except Non200ResponseException as ex:
            return None, ex.response.status_code != 404 and ex.response.status_code != 400

        return json_response, False

    def mark_notification_read(self, notification_name):
        """
        Marks a security scanner notification as read.
        """
        try:
            self._call("DELETE", _API_METHOD_MARK_NOTIFICATION_READ % notification_name)
            return True
        except Non200ResponseException:
            return False
        except requests.exceptions.RequestException:
            logger.exception("Failed to mark notification as read: %s", notification_name)
            return False

    def get_layer_data(self, layer, include_features=False, include_vulnerabilities=False):
        """
        Returns the layer data for the specified layer.

        On error, returns None.
        """
        layer_id = compute_layer_id(layer)
        if layer_id is None:
            return None

        return self._get_layer_data(layer_id, include_features, include_vulnerabilities)

    def _get_layer_data(self, layer_id, include_features=False, include_vulnerabilities=False):
        params = {}
        if include_features:
            params = {"features": True}

        if include_vulnerabilities:
            params = {"vulnerabilities": True}

        try:
            response = self._call("GET", _API_METHOD_GET_LAYER % layer_id, params=params)
            logger.debug(
                "Got response %s for vulnerabilities for layer %s", response.status_code, layer_id
            )
            try:
                return response.json()
            except ValueError:
                logger.exception("Failed to decode response JSON")
                return None

        except Non200ResponseException as ex:
            logger.debug(
                "Got failed response %s for vulnerabilities for layer %s",
                ex.response.status_code,
                layer_id,
            )
            if ex.response.status_code == 404:
                return None
            else:
                logger.error(
                    "downstream security service failure: status %d, text: %s",
                    ex.response.status_code,
                    ex.response.text,
                )
                if ex.response.status_code // 100 == 5:
                    raise APIRequestFailure("Downstream service returned 5xx")
                else:
                    raise APIRequestFailure("Downstream service returned non-200")
        except requests.exceptions.Timeout:
            logger.exception(
                "API call timed out for loading vulnerabilities for layer %s", layer_id
            )
            raise APIRequestFailure("API call timed out")
        except requests.exceptions.ConnectionError:
            logger.exception("Connection error for loading vulnerabilities for layer %s", layer_id)
            raise APIRequestFailure("Could not connect to security service")
        except requests.exceptions.RequestException:
            logger.exception("Failed to get layer data response for %s", layer_id)
            raise APIRequestFailure()

    def _request(self, method, endpoint, path, body, params, timeout):
        """
        Issues an HTTP request to the security endpoint.
        """
        url = _join_api_url(endpoint, self._config.get("SECURITY_SCANNER_API_VERSION", "v1"), path)
        signer_proxy_url = self._config.get("JWTPROXY_SIGNER", "localhost:8081")

        logger.debug("%sing security URL %s", method.upper(), url)
        resp = self._client.request(
            method,
            url,
            json=body,
            params=params,
            timeout=timeout,
            verify=MITM_CERT_PATH,
            headers=DEFAULT_HTTP_HEADERS,
            proxies={"https": "https://" + signer_proxy_url, "http": "http://" + signer_proxy_url},
        )
        if resp.status_code // 100 != 2:
            raise Non200ResponseException(resp)
        return resp

    def _call(self, method, path, params=None, body=None):
        """
        Issues an HTTP request to the security endpoint handling the logic of using an alternative
        BATCH endpoint for non-GET requests and failover for GET requests.
        """
        timeout = self._config.get("SECURITY_SCANNER_API_TIMEOUT_SECONDS", 1)
        endpoint = self._config["SECURITY_SCANNER_ENDPOINT"]

        with CloseForLongOperation(self._config):
            # If the request isn't a read, attempt to use a batch stack and do not fail over.
            if method != "GET":
                if self._config.get("SECURITY_SCANNER_ENDPOINT_BATCH") is not None:
                    endpoint = self._config["SECURITY_SCANNER_ENDPOINT_BATCH"]
                    timeout = (
                        self._config.get("SECURITY_SCANNER_API_BATCH_TIMEOUT_SECONDS") or timeout
                    )
                return self._request(method, endpoint, path, body, params, timeout)

            # The request is read-only and can failover.
            all_endpoints = [endpoint] + self._config.get(
                "SECURITY_SCANNER_READONLY_FAILOVER_ENDPOINTS", []
            )
            return _failover_read_request(
                *[
                    ((self._request, endpoint, path, body, params, timeout), {})
                    for endpoint in all_endpoints
                ]
            )


def _join_api_url(endpoint, api_version, path):
    pathless_url = urljoin(endpoint, "/" + api_version) + "/"
    return urljoin(pathless_url, path)


@failover
def _failover_read_request(request_fn, endpoint, path, body, params, timeout):
    """
    This function auto-retries read-only requests until they return a 2xx status code.
    """
    try:
        return request_fn("GET", endpoint, path, body, params, timeout)
    except (requests.exceptions.RequestException, Non200ResponseException) as ex:
        raise FailoverException(ex)
