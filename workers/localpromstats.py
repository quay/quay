import logging
import time

from prometheus_client import Gauge

from app import app
from health.processes import get_gunicorn_processes, get_all_zombies
from workers.worker import Worker
from util.log import logfile_path


logger = logging.getLogger(__name__)


gunicorn_process_gauge = Gauge("quay_gunicorn_process_count", "count of gunicorn processes")
zombie_process_gauge = Gauge("quay_zombie_process_count", "count of zombie processes")


WORKER_FREQUENCY = app.config["LOCAL_PROMETHEUS_STATS_FREQUENCY"]


def get_gunicorn_process_count():
    """
    Returns the quantity of gunicorn processes running in the local system or namespace.
    """
    return len(get_gunicorn_processes())


def get_zombie_process_count():
    """
    Returns the quantity of zombie processes in the local system or namespace.
    """
    return len(get_all_zombies())


class LocalPrometheusStatsWorker(Worker):
    """
    Worker which reports local stats (# of zombies, processes, etc) to Prometheus periodically.
    """

    def __init__(self):
        super(LocalPrometheusStatsWorker, self).__init__()
        self.add_operation(self._report_stats, WORKER_FREQUENCY)

    def _report_stats(self):
        logger.debug("Reporting local statistics to prometheus.")
        gunicorn_process_gauge.set(get_gunicorn_process_count())
        zombie_process_gauge.set(get_zombie_process_count())


def main():
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    if app.config["FEATURE_REPORT_PROMETHEUS_STATS"]:

        if not app.config.get("PROMETHEUS_PUSHGATEWAY_URL"):
            logger.debug("Prometheus not enabled; skipping local stats reporting")
            while True:
                time.sleep(100000)

        worker = LocalPrometheusStatsWorker()
        worker.start()

    else:
        logger.info("REPORT_PROMETHEUS_STATS feature is disabled. Stopping localpromstats worker.")


if __name__ == "__main__":
    main()
