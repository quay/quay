import logging
import time

from app import app, metric_queue
from data.database import UseThenDisconnect
from workers.globalpromstats.models_pre_oci import pre_oci_model as model
from util.locking import GlobalLock, LockNotAcquiredException
from util.log import logfile_path
from workers.worker import Worker

logger = logging.getLogger(__name__)

WORKER_FREQUENCY = app.config.get('GLOBAL_PROMETHEUS_STATS_FREQUENCY', 60 * 60)


class GlobalPrometheusStatsWorker(Worker):
  """ Worker which reports global stats (# of users, orgs, repos, etc) to Prometheus periodically.
  """
  def __init__(self):
    super(GlobalPrometheusStatsWorker, self).__init__()
    self.add_operation(self._try_report_stats, WORKER_FREQUENCY)

  def _try_report_stats(self):
    logger.debug('Attempting to report stats')

    try:
      with GlobalLock('GLOBAL_PROM_STATS'):
        self._report_stats()
    except LockNotAcquiredException:
      logger.debug('Could not acquire global lock for global prometheus stats')
      return

  def _report_stats(self):
    logger.debug('Reporting global stats')
    with UseThenDisconnect(app.config):
      # Repository count.
      metric_queue.repository_count.Set(model.get_repository_count())

      # User counts.
      metric_queue.user_count.Set(model.get_active_user_count())
      metric_queue.org_count.Set(model.get_active_org_count())
      metric_queue.robot_count.Set(model.get_robot_count())


def main():
  logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

  if not app.config.get('PROMETHEUS_AGGREGATOR_URL'):
    logger.debug('Prometheus not enabled; skipping global stats reporting')
    while True:
      time.sleep(100000)

  worker = GlobalPrometheusStatsWorker()
  worker.start()


if __name__ == "__main__":
  main()
