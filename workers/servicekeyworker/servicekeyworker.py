import logging
from datetime import datetime, timedelta

from prometheus_client import Counter

from app import app, instance_keys
from workers.servicekeyworker.models_pre_oci import pre_oci_model as model
from workers.worker import Worker


logger = logging.getLogger(__name__)


instance_key_renewal_self = Counter(
    "quay_instance_key_renewal_self_total",
    "number of times a Quay instance renews its own key",
    labelnames=["success"],
)


class ServiceKeyWorker(Worker):
    def __init__(self):
        super(ServiceKeyWorker, self).__init__()
        self.add_operation(
            self._refresh_service_key, app.config.get("INSTANCE_SERVICE_KEY_REFRESH", 60) * 60
        )

    def _refresh_service_key(self):
        """
        Refreshes the instance's active service key so it doesn't get garbage collected.
        """
        expiration_time = timedelta(minutes=instance_keys.service_key_expiration)
        new_expiration = datetime.utcnow() + expiration_time

        logger.debug(
            "Starting automatic refresh of service key %s to new expiration %s",
            instance_keys.local_key_id,
            new_expiration,
        )
        try:
            model.set_key_expiration(instance_keys.local_key_id, new_expiration)
        except Exception as ex:
            logger.exception(
                "Failure for automatic refresh of service key %s with new expiration %s",
                instance_keys.local_key_id,
                new_expiration,
            )
            instance_key_renewal_self.labels(False).inc()
            raise ex

        logger.debug(
            "Finished automatic refresh of service key %s with new expiration %s",
            instance_keys.local_key_id,
            new_expiration,
        )
        instance_key_renewal_self.labels(True).inc()


if __name__ == "__main__":
    worker = ServiceKeyWorker()
    worker.start()
