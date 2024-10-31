import json
import logging
import ssl

from splunklib import client

from data.logs_model.logs_producer import LogSendException
from data.logs_model.logs_producer.interface import LogProducerInterface

logger = logging.getLogger(__name__)


class SplunkLogsProducer(LogProducerInterface):
    """
    Log producer for writing log entries to Splunk
    This implementation writes directly to Splunk without a streaming/queueing service.
    """

    def __init__(
        self,
        host,
        port,
        bearer_token,
        url_scheme="https",
        verify_ssl=True,
        index_prefix=None,
        ssl_ca_path=None,
    ):
        connect_args = {
            "host": host,
            "port": port,
            "token": bearer_token,
            "scheme": url_scheme,
            "verify": verify_ssl,
            "autologin": True,
        }
        # Create an SSLContext object for cert validation
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        if not verify_ssl:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        if ssl_ca_path:
            try:
                context.load_verify_locations(cafile=ssl_ca_path)
            except ssl.SSLError as e:
                raise Exception("SSL cert is not valid %s" % e)
            except FileNotFoundError as e:
                raise Exception("Path to cert file is not valid %s" % e)
        connect_args["context"] = context

        # establish connection with splunk
        service = client.connect(**connect_args)
        try:
            self.index = service.indexes[index_prefix]
            logger.info("using existing splunk index %s", self.index)
        except KeyError:
            self.index = service.indexes.create(index_prefix)
            logger.info("Created new splunk index %s", self.index)
        except ConnectionRefusedError as e:
            raise Exception(
                "Connection to Splunk refused, check if Splunk instance is available: %s" % e
            )

    def send(self, log):
        try:
            log_data = json.dumps(log, sort_keys=True, default=str, ensure_ascii=False).encode(
                "utf-8"
            )
            self.index.submit(log_data, sourcetype="access_combined", host="quay")
        except Exception as e:
            logger.exception("SplunkLogsProducer exception sending log to Splunk: %s", e)
            raise LogSendException("SplunkLogsProducer exception sending log to Splunk: %s" % e)
