import logging
from datetime import datetime, timedelta

from app import app, instance_keys, metric_queue
from workers.servicekeyworker.models_pre_oci import pre_oci_model as model
from workers.worker import Worker

logger = logging.getLogger(__name__)


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
            metric_queue.instance_key_renewal_failure.Inc(labelvalues=[instance_keys.local_key_id])
            raise ex

        logger.debug(
            "Finished automatic refresh of service key %s with new expiration %s",
            instance_keys.local_key_id,
            new_expiration,
        )
        metric_queue.instance_key_renewal_success.Inc(labelvalues=[instance_keys.local_key_id])


if __name__ == "__main__":
    worker = ServiceKeyWorker()
    worker.start()
