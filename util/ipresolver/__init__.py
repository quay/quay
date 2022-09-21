import logging
import json
import time
import os

from collections import namedtuple

from threading import Thread, Lock
from abc import ABCMeta, abstractmethod
from six import add_metaclass
from cachetools.func import ttl_cache, lru_cache
from netaddr import IPNetwork, IPAddress, IPSet, AddrFormatError

import geoip2.database
import geoip2.errors
import requests
from typing import Dict

from util.abchelpers import nooper

ResolvedLocation = namedtuple(
    "ResolvedLocation", ["provider", "service", "sync_token", "country_iso_code", "aws_region"]
)

AWS_SERVICES = {"EC2", "CODEBUILD"}

logger = logging.getLogger(__name__)


def _get_aws_ip_ranges():
    try:
        # resolve absolute path to file
        path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(path, "aws-ip-ranges.json")
        with open(file_path, "r") as f:
            return json.loads(f.read())
    except IOError:
        logger.exception("Could not load AWS IP Ranges")
        return None
    except ValueError:
        logger.exception("Could not load AWS IP Ranges")
        return None
    except TypeError:
        logger.exception("Could not load AWS IP Ranges")
        return None


@add_metaclass(ABCMeta)
class IPResolverInterface(object):
    """
    Helper class for resolving information about an IP address.
    """

    @abstractmethod
    def resolve_ip(self, ip_address):
        """
        Attempts to return resolved information about the specified IP Address.

        If such an attempt fails, returns None.
        """
        pass

    @abstractmethod
    def is_ip_possible_threat(self, ip_address):
        """
        Attempts to return whether the given IP address is a possible abuser or spammer.

        Returns False if the IP address information could not be looked up.
        """
        pass


@nooper
class NoopIPResolver(IPResolverInterface):
    """
    No-op version of the security scanner API.
    """

    pass


class IPResolver(IPResolverInterface):
    def __init__(self, app):
        self.app = app

        # resolve absolute path to file
        path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(path, "GeoLite2-Country.mmdb")
        self.geoip_db = geoip2.database.Reader(file_path)

        self.amazon_ranges: Dict[str, IPSet] = None
        self.sync_token = None

        logger.info("Loading AWS IP ranges from disk")
        aws_ip_ranges_data = _get_aws_ip_ranges()
        if aws_ip_ranges_data is not None and aws_ip_ranges_data.get("syncToken"):
            logger.debug("Building AWS IP ranges")
            self.amazon_ranges = IPResolver._parse_amazon_ranges(aws_ip_ranges_data)
            self.sync_token = aws_ip_ranges_data["syncToken"]
            logger.debug("Finished building AWS IP ranges")

    @ttl_cache(maxsize=100, ttl=600)
    def is_ip_possible_threat(self, ip_address):
        if self.app.config.get("THREAT_NAMESPACE_MAXIMUM_BUILD_COUNT") is None:
            return False

        if self.app.config.get("IP_DATA_API_KEY") is None:
            return False

        if not ip_address:
            return False

        api_key = self.app.config["IP_DATA_API_KEY"]

        try:
            logger.debug("Requesting IP data for IP %s", ip_address)
            r = requests.get(
                "https://api.ipdata.co/%s/threat?api-key=%s" % (ip_address, api_key), timeout=1
            )
            if r.status_code != 200:
                logger.debug("Got non-200 response for IP %s: %s", ip_address, r.status_code)
                return False

            logger.debug("Got IP data for IP %s: %s => %s", ip_address, r.status_code, r.json())
            threat_data = r.json()
            return threat_data.get("is_threat", False) or threat_data.get("is_bogon", False)
        except requests.RequestException:
            logger.exception("Got exception when trying to lookup IP Address")
        except ValueError:
            logger.exception("Got exception when trying to lookup IP Address")
        except Exception:
            logger.exception("Got exception when trying to lookup IP Address")

        return False

    def resolve_ip(self, ip_address):
        """
        Attempts to return resolved information about the specified IP Address.

        If such an attempt fails, returns None.
        """
        if not ip_address:
            return None

        try:
            parsed_ip = IPAddress(ip_address)
        except AddrFormatError:
            return ResolvedLocation("invalid_ip", None, self.sync_token, None, None)

        # Try geoip classification
        try:
            geoinfo = self.geoip_db.country(ip_address)
        except geoip2.errors.AddressNotFoundError:
            geoinfo = None

        aws_region = self.get_aws_ip_region(parsed_ip)

        # Not an AWS IP
        if not aws_region:
            if geoinfo:
                return ResolvedLocation(
                    "internet",
                    geoinfo.country.iso_code,
                    self.sync_token,
                    geoinfo.country.iso_code,
                    None,
                )

            return ResolvedLocation("internet", None, self.sync_token, None, None)

        return ResolvedLocation(
            "aws", None, self.sync_token, geoinfo.country.iso_code if geoinfo else None, aws_region
        )

    def get_aws_ip_region(self, ip_address: IPAddress):
        if not self.amazon_ranges:
            return None

        for region in self.amazon_ranges:
            ipset = self.amazon_ranges[region]
            if ip_address in ipset:
                return region
        return None

    @staticmethod
    def _parse_amazon_ranges(ranges):
        all_amazon = {}
        for service_description in ranges["prefixes"]:
            region = service_description["region"]
            service = service_description["service"]

            if region not in all_amazon:
                all_amazon[region] = IPSet()

            if service in AWS_SERVICES:
                all_amazon[region].add(IPNetwork(service_description["ip_prefix"]))

        return all_amazon
