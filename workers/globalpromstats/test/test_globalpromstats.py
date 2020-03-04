from workers.globalpromstats.globalpromstats import GlobalPrometheusStatsWorker

from test.fixtures import *


def test_globalpromstats(initialized_db):
    worker = GlobalPrometheusStatsWorker()
    worker._report_stats()
