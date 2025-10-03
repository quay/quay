"""
Redis Pull Metrics Flush Worker Entry Point

Main entry point for the Redis flush worker that handles flushing pull metrics
from Redis to persistent database storage.
"""

import logging.config
import time

import features
from app import app
from util.locking import GlobalLock
from util.log import logfile_path
from workers.gunicorn_worker import GunicornWorker
from workers.redisflushworker.redis_pull_metrics_worker import RedisFlushWorker
from workers.worker import Worker

logger = logging.getLogger(__name__)


def create_gunicorn_worker():
    """Create the Gunicorn worker instance."""
    # Check if pull metrics Redis is configured
    if not app.config.get("PULL_METRICS_REDIS"):
        logger.info("PULL_METRICS_REDIS not configured; skipping redis flush worker")
        return None

    worker = GunicornWorker(__name__, app, RedisFlushWorker(), features.PULL_METRICS_ANALYTICS)
    return worker


if __name__ == "__main__":
    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    # Check if pull metrics analytics is enabled
    if not features.PULL_METRICS_ANALYTICS:
        logger.debug("Pull metrics analytics disabled; skipping redis flush worker")
        while True:
            time.sleep(100000)

    # Check if Redis is configured
    if not app.config.get("PULL_METRICS_REDIS"):
        logger.debug("PULL_METRICS_REDIS not configured; skipping redis flush worker")
        while True:
            time.sleep(100000)

    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)
    worker = RedisFlushWorker()
    worker.start()
