import logging
import time
import random

from queue import Empty
from threading import Thread

import boto


logger = logging.getLogger(__name__)


MAX_BATCH_METRICS = 20

# Sleep for this much time between failed send requests.
# This prevents hammering cloudwatch when it's not available.
FAILED_SEND_SLEEP_SECS = 15


def start_cloudwatch_sender(metrics, app):
    """
    Starts sending from metrics to a new CloudWatchSender.
    """
    access_key = app.config.get("CLOUDWATCH_AWS_ACCESS_KEY")
    secret_key = app.config.get("CLOUDWATCH_AWS_SECRET_KEY")
    namespace = app.config.get("CLOUDWATCH_NAMESPACE")

    if not namespace:
        logger.debug("CloudWatch not configured")
        return

    sender = CloudWatchSender(metrics, access_key, secret_key, namespace)
    sender.start()


class CloudWatchSender(Thread):
    """
    CloudWatchSender loops indefinitely and pulls metrics off of a queue then sends it to
    CloudWatch.
    """

    def __init__(self, metrics, aws_access_key, aws_secret_key, namespace):
        Thread.__init__(self)
        self.daemon = True

        self._aws_access_key = aws_access_key
        self._aws_secret_key = aws_secret_key
        self._metrics = metrics
        self._namespace = namespace

    def run(self):
        try:
            logger.debug("Starting CloudWatch sender process.")
            connection = boto.connect_cloudwatch(self._aws_access_key, self._aws_secret_key)
        except:
            logger.exception("Failed to connect to CloudWatch.")
        self._metrics.enable_deprecated()

        while True:
            metrics = {
                "name": [],
                "value": [],
                "unit": [],
                "timestamp": [],
                "dimensions": [],
            }

            metric = self._metrics.get_deprecated()
            append_metric(metrics, metric)

            while len(metrics["name"]) < MAX_BATCH_METRICS:
                try:
                    metric = self._metrics.get_nowait_deprecated()
                    append_metric(metrics, metric)
                except Empty:
                    break

            try:
                connection.put_metric_data(self._namespace, **metrics)
                logger.debug("Sent %d CloudWatch metrics", len(metrics["name"]))
            except:
                for i in range(len(metrics["name"])):
                    self._metrics.put_deprecated(
                        metrics["name"][i],
                        metrics["value"][i],
                        unit=metrics["unit"][i],
                        dimensions=metrics["dimensions"][i],
                        timestamp=metrics["timestamp"][i],
                    )

                logger.exception("Failed to write to CloudWatch: %s", metrics)
                logger.debug("Attempted to requeue %d metrics.", len(metrics["name"]))
                # random int between 1/2 and 1 1/2 of FAILED_SEND_SLEEP duration
                sleep_secs = random.randint(
                    FAILED_SEND_SLEEP_SECS / 2, 3 * FAILED_SEND_SLEEP_SECS / 2
                )
                time.sleep(sleep_secs)


def append_metric(metrics, m):
    name, value, kwargs = m
    metrics["name"].append(name)
    metrics["value"].append(value)
    metrics["unit"].append(kwargs.get("unit"))
    metrics["dimensions"].append(kwargs.get("dimensions"))
    metrics["timestamp"].append(kwargs.get("timestamp"))
