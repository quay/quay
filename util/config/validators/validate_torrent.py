import logging

from hashlib import sha1

from util.config.validators import BaseValidator, ConfigValidationException
from util.registry.torrent import jwt_from_infohash, TorrentConfiguration

logger = logging.getLogger(__name__)


class BittorrentValidator(BaseValidator):
    name = "bittorrent"

    @classmethod
    def validate(cls, validator_context):
        """
        Validates the configuration for using BitTorrent for downloads.
        """
        config = validator_context.config
        client = validator_context.http_client

        announce_url = config.get("BITTORRENT_ANNOUNCE_URL")
        if not announce_url:
            raise ConfigValidationException("Missing announce URL")

        # Ensure that the tracker is reachable and accepts requests signed with a registry key.
        params = {
            "info_hash": sha1(b"test").digest(),
            "peer_id": "-QUAY00-6wfG2wk6wWLc",
            "uploaded": 0,
            "downloaded": 0,
            "left": 0,
            "numwant": 0,
            "port": 80,
        }

        torrent_config = TorrentConfiguration.for_testing(
            validator_context.instance_keys, announce_url, validator_context.registry_title
        )
        encoded_jwt = jwt_from_infohash(torrent_config, params["info_hash"])
        params["jwt"] = encoded_jwt

        resp = client.get(announce_url, timeout=5, params=params)
        logger.debug("Got tracker response: %s: %s", resp.status_code, resp.text)

        if resp.status_code == 404:
            raise ConfigValidationException("Announce path not found; did you forget `/announce`?")

        if resp.status_code == 500:
            raise ConfigValidationException(
                "Did not get expected response from Tracker; " + "please check your settings"
            )

        if resp.status_code == 200:
            if "invalid jwt" in resp.text:
                raise ConfigValidationException(
                    "Could not authorize to Tracker; is your Tracker " + "properly configured?"
                )

            if "failure reason" in resp.text:
                raise ConfigValidationException(
                    "Could not validate signed announce request: " + resp.text
                )

            if "go_goroutines" in resp.text:
                raise ConfigValidationException(
                    "Could not validate signed announce request: "
                    + "provided port is used for Prometheus"
                )
