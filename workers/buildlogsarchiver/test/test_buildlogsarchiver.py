from mock import patch, Mock

from app import storage
from workers.buildlogsarchiver.buildlogsarchiver import ArchiveBuildLogsWorker

from test.fixtures import *

from workers.buildlogsarchiver.models_pre_oci import pre_oci_model as model


def test_logarchiving(app):
    worker = ArchiveBuildLogsWorker()
    logs_mock = Mock()
    logs_mock.get_log_entries = Mock(return_value=(1, [{"some": "entry"}]))

    # Add a build that is ready for archiving.
    build = model.create_build_for_testing()

    with patch("workers.buildlogsarchiver.buildlogsarchiver.build_logs", logs_mock):
        worker._archive_redis_buildlogs()

    # Ensure the get method was called.
    logs_mock.get_log_entries.assert_called_once()
    logs_mock.expire_status.assert_called_once()
    logs_mock.delete_log_entries.assert_called_once()

    # Ensure the build was marked as archived.
    assert model.get_build(build.uuid).logs_archived

    # Ensure a file was written to storage.
    assert storage.exists(["local_us"], "logarchive/%s" % build.uuid)
