import json
import logging

import requests

from data.logs_model.logs_producer import LogSendException
from data.logs_model.logs_producer.interface import LogProducerInterface
from data.model import config

logger = logging.getLogger(__name__)


class SplunkHECLogsProducer(LogProducerInterface):
    """
    Log producer for writing log entries to Splunk via HTTP Event Collector (HEC).
    """

    def __init__(
        self,
        host,
        port,
        hec_token,
        url_scheme="https",
        verify_ssl=True,
        ssl_ca_path=None,
        index=None,
        splunk_host=None,
        splunk_sourcetype=None,
    ):
        splunk_port = port if port else (443 if verify_ssl else 80)
        self.hec_url = f"{url_scheme}://{host}:{splunk_port}/services/collector/event"
        self.headers = {"Authorization": f"Splunk {hec_token}", "Content-Type": "application/json"}
        self.verify_ssl = verify_ssl
        if not verify_ssl:
            self.ssl_verify_context = False
        else:
            self.ssl_verify_context = ssl_ca_path if ssl_ca_path else True

        self.index = index
        self.splunk_host = splunk_host
        self.splunk_sourcetype = splunk_sourcetype

    def send(self, log):
        try:
            host = self.splunk_host if self.splunk_host else config.app_config["SERVER_HOSTNAME"]
            sourcetype = self.splunk_sourcetype if self.splunk_sourcetype else "access_combined"

            log_event = {
                "event": log,
                "sourcetype": sourcetype,
                "host": host,
            }

            if self.index:
                log_event["index"] = self.index

            log_data = json.dumps(
                log_event, sort_keys=True, default=str, ensure_ascii=False
            ).encode("utf-8")

            response = requests.post(
                self.hec_url,
                headers=self.headers,
                data=log_data,
                verify=self.ssl_verify_context,
            )
            response.raise_for_status()
        except Exception as e:
            logger.exception("Failed to send log to Splunk via HEC: %s", e)
            raise LogSendException(f"Failed to send log to Splunk via HEC: {e}")
