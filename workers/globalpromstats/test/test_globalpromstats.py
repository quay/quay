from mock import patch, Mock

from workers.globalpromstats.globalpromstats import GlobalPrometheusStatsWorker

from test.fixtures import *

def test_reportstats(initialized_db):
  mock = Mock()
  with patch('workers.globalpromstats.globalpromstats.metric_queue', mock):
    worker = GlobalPrometheusStatsWorker()
    worker._report_stats()

  mock.repository_count.Set.assert_called_once()
  mock.org_count.Set.assert_called_once()
  mock.robot_count.Set.assert_called_once()
