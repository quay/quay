from test.fixtures import *

from workers.globalpromstats.globalpromstats import GlobalPrometheusStatsWorker


def test_globalpromstats(initialized_db):
    worker = GlobalPrometheusStatsWorker()
    worker._report_stats()
