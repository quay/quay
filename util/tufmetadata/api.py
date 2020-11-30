import logging

from urllib.parse import urljoin
from posixpath import join

from abc import ABCMeta, abstractmethod
from six import add_metaclass

import requests

from data.database import CloseForLongOperation
from util.abchelpers import nooper
from util.failover import failover, FailoverException
from util.security.instancekeys import InstanceKeys
from util.security.registry_jwt import (
    build_context_and_subject,
    generate_bearer_token,
    SIGNER_TUF_ROOT,
)


DEFAULT_HTTP_HEADERS = {"Connection": "close"}
MITM_CERT_PATH = "/conf/mitm.cert"
TOKEN_VALIDITY_LIFETIME_S = 60 * 60  # 1 hour

logger = logging.getLogger(__name__)


class InvalidMetadataException(Exception):
    """
    Exception raised when the upstream API metadata that doesn't parse correctly.
    """

    pass


class Non200ResponseException(Exception):
    """
    Exception raised when the upstream API returns a non-200 HTTP status code.
    """

    def __init__(self, response):
        super(Non200ResponseException, self).__init__()
        self.response = response


class TUFMetadataAPI(object):
    """
    Helper class for talking to the TUF Metadata service (Apostille).
    """

    def __init__(self, app, config, client=None):
        feature_enabled = config.get("FEATURE_SIGNING", False)
        if feature_enabled:
            self.state = ImplementedTUFMetadataAPI(app, config, client=client)
        else:
            self.state = NoopTUFMetadataAPI()

    def __getattr__(self, name):
        return getattr(self.state, name, None)


@add_metaclass(ABCMeta)
class TUFMetadataAPIInterface(object):
    """
    Helper class for talking to the TUF Metadata service (Apostille).
    """

    @abstractmethod
    def get_default_tags_with_expiration(self, namespace, repository, targets_file=None):
        """
        Gets the tag -> sha mappings for a repo, as well as the expiration of the signatures. Does
        not verify the metadata, this is purely for display purposes.

        Args:
          namespace: namespace containing the repository
          repository: the repo to get tags for
          targets_file: the specific delegation to read from. Default: targets/releases.json

        Returns:
          targets, expiration or None, None
        """
        pass

    @abstractmethod
    def get_all_tags_with_expiration(
        self, namespace, repository, targets_file=None, targets_map=None
    ):
        """
        Gets the tag -> sha mappings of all delegations for a repo, as well as the expiration of the
        signatures. Does not verify the metadata, this is purely for display purposes.

        Args:
          namespace: namespace containing the repository
          repository: the repo to get tags for
          targets_file: the specific target or delegation to read from. Default: targets.json

        Returns:
          targets
        """
        pass

    @abstractmethod
    def delete_metadata(self, namespace, repository):
        """
        Deletes the TUF metadata for a repo.

        Args:
          namespace: namespace containing the repository
          repository: the repo to delete metadata for

        Returns:
           True if successful, False otherwise
        """
        pass


@nooper
class NoopTUFMetadataAPI(TUFMetadataAPIInterface):
    """
    No-op version of the TUF API.
    """

    pass


class ImplementedTUFMetadataAPI(TUFMetadataAPIInterface):
    def __init__(self, app, config, client=None):
        self._app = app
        self._instance_keys = InstanceKeys(app)
        self._config = config
        self._client = client or config["HTTPCLIENT"]
        self._gun_prefix = config["TUF_GUN_PREFIX"] or config["SERVER_HOSTNAME"]

    def get_default_tags_with_expiration(self, namespace, repository, targets_file=None):
        """
        Gets the tag -> sha mappings for a repo, as well as the expiration of the signatures. Does
        not verify the metadata, this is purely for display purposes.

        Args:
          namespace: namespace containing the repository
          repository: the repo to get tags for
          targets_file: the specific delegation to read from. Default: targets/releases.json

        Returns:
          targets, expiration or None, None
        """

        if not targets_file:
            targets_file = "targets/releases.json"

        signed = self._get_signed(namespace, repository, targets_file)
        if not signed:
            return None, None

        return signed.get("targets"), signed.get("expires")

    def get_all_tags_with_expiration(
        self, namespace, repository, targets_file=None, targets_map=None
    ):
        """
        Gets the tag -> sha mappings of all delegations for a repo, as well as the expiration of the
        signatures. Does not verify the metadata, this is purely for display purposes.

        Args:
          namespace: namespace containing the repository
          repository: the repo to get tags for
          targets_file: the specific target or delegation to read from. Default: targets.json

        Returns:
          targets
        """

        if not targets_file:
            targets_file = "targets.json"

        targets_name = targets_file
        if targets_name.endswith(".json"):
            targets_name = targets_name[:-5]

        if not targets_map:
            targets_map = {}

        signed = self._get_signed(namespace, repository, targets_file)
        if not signed:
            targets_map[targets_name] = None
            return targets_map

        if signed.get("targets"):
            targets_map[targets_name] = {
                "targets": signed.get("targets"),
                "expiration": signed.get("expires"),
            }

        delegation_names = [role.get("name") for role in signed.get("delegations").get("roles")]

        for delegation in delegation_names:
            targets_map = self.get_all_tags_with_expiration(
                namespace, repository, targets_file=delegation + ".json", targets_map=targets_map
            )

        return targets_map

    def delete_metadata(self, namespace, repository):
        """
        Deletes the TUF metadata for a repo.

        Args:
          namespace: namespace containing the repository
          repository: the repo to delete metadata for

        Returns:
           True if successful, False otherwise
        """
        gun = self._gun(namespace, repository)
        try:
            self._delete(gun)
        except requests.exceptions.Timeout:
            logger.exception("Timeout when trying to delete metadata for %s", gun)
            return False
        except requests.exceptions.ConnectionError:
            logger.exception("Connection error when trying to delete metadata for %s", gun)
            return False
        except (requests.exceptions.RequestException, ValueError):
            logger.exception("Failed to delete metadata for %s", gun)
            return False
        except Non200ResponseException as ex:
            logger.exception("Failed request for %s: %s %s", gun, ex.response, str(ex))
            return False
        return True

    def _gun(self, namespace, repository):
        return join(self._gun_prefix, namespace, repository)

    def _get_signed(self, namespace, repository, targets_file):
        gun = self._gun(namespace, repository)

        try:
            response = self._get(gun, targets_file)
            signed = self._parse_signed(response.json())
            return signed
        except requests.exceptions.Timeout:
            logger.exception("Timeout when trying to get metadata for %s", gun)
        except requests.exceptions.ConnectionError:
            logger.exception("Connection error when trying to get metadata for %s", gun)
        except (requests.exceptions.RequestException, ValueError):
            logger.exception("Failed to get metadata for %s", gun)
        except Non200ResponseException as ex:
            logger.exception("Failed request for %s: %s %s", gun, ex.response, str(ex))
        except InvalidMetadataException as ex:
            logger.exception("Failed to parse targets from metadata: %s", str(ex))
        return None

    def _parse_signed(self, json_response):
        """
        Attempts to parse the targets from a metadata response.
        """
        signed = json_response.get("signed")
        if not signed:
            raise InvalidMetadataException(
                "Could not find `signed` in metadata: %s" % json_response
            )
        return signed

    def _auth_header(self, gun, actions):
        """
        Generate a registry auth token for apostille.
        """
        access = [
            {
                "type": "repository",
                "name": gun,
                "actions": actions,
            }
        ]
        context, subject = build_context_and_subject(
            auth_context=None, tuf_roots={gun: SIGNER_TUF_ROOT}
        )
        token = generate_bearer_token(
            self._config["SERVER_HOSTNAME"],
            subject,
            context,
            access,
            TOKEN_VALIDITY_LIFETIME_S,
            self._instance_keys,
        )
        return {"Authorization": "Bearer %s" % token.decode("ascii")}

    def _get(self, gun, metadata_file):
        return self._call(
            "GET",
            "/v2/%s/_trust/tuf/%s" % (gun, metadata_file),
            headers=self._auth_header(gun, ["pull"]),
        )

    def _delete(self, gun):
        return self._call(
            "DELETE", "/v2/%s/_trust/tuf/" % (gun), headers=self._auth_header(gun, ["*"])
        )

    def _request(self, method, endpoint, path, body, headers, params, timeout):
        """
        Issues an HTTP request to the signing endpoint.
        """
        url = urljoin(endpoint, path)
        logger.debug("%sing signing URL %s", method.upper(), url)

        headers.update(DEFAULT_HTTP_HEADERS)
        resp = self._client.request(
            method, url, json=body, params=params, timeout=timeout, verify=True, headers=headers
        )
        if resp.status_code // 100 != 2:
            raise Non200ResponseException(resp)
        return resp

    def _call(self, method, path, params=None, body=None, headers=None):
        """
        Issues an HTTP request to signing service and handles failover for GET requests.
        """
        timeout = self._config.get("TUF_API_TIMEOUT_SECONDS", 1)
        endpoint = self._config["TUF_SERVER"]

        with CloseForLongOperation(self._config):
            # If the request isn't a read do not fail over.
            if method != "GET":
                return self._request(method, endpoint, path, body, headers, params, timeout)

            # The request is read-only and can failover.
            all_endpoints = [endpoint] + self._config.get("TUF_READONLY_FAILOVER_ENDPOINTS", [])
            return _failover_read_request(
                *[
                    ((self._request, endpoint, path, body, headers, params, timeout), {})
                    for endpoint in all_endpoints
                ]
            )


@failover
def _failover_read_request(request_fn, endpoint, path, body, headers, params, timeout):
    """
    This function auto-retries read-only requests until they return a 2xx status code.
    """
    try:
        return request_fn("GET", endpoint, path, body, headers, params, timeout)
    except (requests.exceptions.RequestException, Non200ResponseException) as ex:
        raise FailoverException(ex)
