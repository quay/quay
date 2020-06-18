import logging
import etcd

logger = logging.getLogger(__name__)


class EtcdCanceller(object):
    """
    A class that sends a message to etcd to cancel a build.
    """

    def __init__(self, config):
        etcd_host = config.get("ETCD_HOST", "127.0.0.1")
        etcd_port = config.get("ETCD_PORT", 2379)
        etcd_ca_cert = config.get("ETCD_CA_CERT", None)
        etcd_auth = config.get("ETCD_CERT_AND_KEY", None)
        if etcd_auth is not None:
            etcd_auth = tuple(etcd_auth)

        etcd_protocol = "http" if etcd_auth is None else "https"
        logger.debug("Connecting to etcd on %s:%s", etcd_host, etcd_port)
        self._cancel_prefix = config.get("ETCD_CANCEL_PREFIX", "cancel/")
        self._etcd_client = etcd.Client(
            host=etcd_host,
            port=etcd_port,
            cert=etcd_auth,
            ca_cert=etcd_ca_cert,
            protocol=etcd_protocol,
            read_timeout=5,
        )

    def try_cancel_build(self, build_uuid):
        """
        Writes etcd message to cancel build_uuid.
        """
        logger.debug("Cancelling build %s".format(build_uuid))
        try:
            self._etcd_client.write(
                "{}{}".format(self._cancel_prefix, build_uuid), build_uuid, ttl=60
            )
            return True
        except etcd.EtcdException:
            logger.exception("Failed to write to etcd client %s", build_uuid)
            return False
