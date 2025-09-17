import logging
import random
import time
from queue import Empty
from threading import Thread

import boto

from util.aws_sts import create_aws_client

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
    region = app.config.get("CLOUDWATCH_AWS_REGION", "us-east-1")

    role_arn = app.config.get("CLOUDWATCH_ROLE_ARN")
    role_session_name = app.config.get("CLOUDWATCH_ROLE_SESSION_NAME", "quay-cloudwatch-sender")
    web_identity_token_file = app.config.get("CLOUDWATCH_WEB_IDENTITY_TOKEN_FILE")

    if not namespace:
        logger.debug("CloudWatch not configured")
        return

    sender = CloudWatchSender(metrics, access_key, secret_key, namespace, region, role_arn)
    sender.start()


class CloudWatchSender(Thread):
    """
    CloudWatchSender loops indefinitely and pulls metrics off of a queue then sends it to
    CloudWatch.
    """

    def __init__(
        self,
        metrics,
        aws_access_key,
        aws_secret_key,
        namespace,
        region,
        aws_role_arn=None,
        aws_session_name=None,
        aws_web_identity_token_file=None,
    ):
        Thread.__init__(self)
        self.daemon = True

        self._aws_access_key = aws_access_key
        self._aws_secret_key = aws_secret_key
        self._metrics = metrics
        self._namespace = namespace
        self._region = region
        self._aws_role_arn = aws_role_arn
        self._aws_session_name = aws_session_name
        self._aws_web_identity_token_file = aws_web_identity_token_file

    def run(self):
        try:
            logger.debug("Starting CloudWatch sender process.")

            self._cloudwatch_client = create_aws_client(
                service_name="cloudwatch",
                region=self._region,
                access_key=self._aws_access_key,
                secret_key=self._aws_secret_key,
                role_arn=self._aws_role_arn,
                session_name=self._aws_session_name,
                web_identity_token_file=self._aws_web_identity_token_file,
            )
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
                # Convert metrics to boto3 format
                metric_data = []
                for i in range(len(metrics["name"])):
                    metric = {
                        "MetricName": metrics["name"][i],
                        "Value": metrics["value"][i],
                    }
                    if metrics["unit"][i]:
                        metric["Unit"] = metrics["unit"][i]
                    if metrics["timestamp"][i]:
                        metric["Timestamp"] = metrics["timestamp"][i]
                    if metrics["dimensions"][i]:
                        metric["Dimensions"] = [
                            {"Name": k, "Value": v} for k, v in metrics["dimensions"][i].items()
                        ]
                    metric_data.append(metric)

                self._cloudwatch_client.put_metric_data(
                    Namespace=self._namespace, MetricData=metric_data
                )
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
