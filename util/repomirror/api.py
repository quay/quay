import logging

from abc import ABCMeta, abstractmethod
from six import add_metaclass
import requests
from util.abchelpers import nooper
from util.repomirror.validator import RepoMirrorConfigValidator

TOKEN_VALIDITY_LIFETIME_S = 60  # Amount of time the repo mirror has to call the skopeo URL

DEFAULT_HTTP_HEADERS = {"Connection": "close"}

logger = logging.getLogger(__name__)


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


_API_METHOD_PING = "metrics"


class RepoMirrorAPI(object):
    """
    Helper class for talking to the Repository Mirror service (usually Skopeo).
    """

    def __init__(self, config, server_hostname=None, skip_validation=False, instance_keys=None):
        feature_enabled = config.get("FEATURE_REPO_MIRROR", False)
        has_valid_config = skip_validation

        if not skip_validation and feature_enabled:
            config_validator = RepoMirrorConfigValidator(feature_enabled)
            has_valid_config = config_validator.valid()

        self.state = NoopRepoMirrorAPI()
        if feature_enabled and has_valid_config:
            self.state = ImplementedRepoMirrorAPI(
                config, server_hostname, instance_keys=instance_keys
            )

    def __getattr__(self, name):
        return getattr(self.state, name, None)


@add_metaclass(ABCMeta)
class RepoMirrorAPIInterface(object):
    """
    Helper class for talking to the Repository Mirror service (usually Skopeo Worker).
    """

    @abstractmethod
    def ping(self):
        """
        Calls GET on the metrics endpoint of the repo mirror to ensure it is running and properly
        configured.

        Returns the HTTP response.
        """
        pass


@nooper
class NoopRepoMirrorAPI(RepoMirrorAPIInterface):
    """
    No-op version of the repo mirror API.
    """

    pass


class ImplementedRepoMirrorAPI(RepoMirrorAPIInterface):
    """
    Helper class for talking to the repo mirror service.
    """

    def __init__(self, config, server_hostname, client=None, instance_keys=None):
        self._config = config
        self._instance_keys = instance_keys
        self._client = client

    def ping(self):
        """
        Calls GET on the metrics endpoint of the repository mirror to ensure it is running and
        properly configured.

        Returns the HTTP response.
        """
        try:
            return self._call("GET", _API_METHOD_PING)
        except requests.exceptions.Timeout as tie:
            logger.exception("Timeout when trying to connect to repository mirror endpoint")
            msg = "Timeout when trying to connect to repository mirror endpoint: %s" % str(tie)
            raise Exception(msg)
        except requests.exceptions.ConnectionError as ce:
            logger.exception(
                "Connection error when trying to connect to repository mirror endpoint"
            )
            msg = "Connection error when trying to connect to repository mirror endpoint: %s" % str(
                ce
            )
            raise Exception(msg)
        except (requests.exceptions.RequestException, ValueError) as ve:
            logger.exception("Exception when trying to connect to repository mirror endpoint")
            msg = "Exception when trying to connect to repository mirror endpoint: %s" % str(ve)
            raise Exception(msg)
