# complete code
import pytest
from unittest.mock import patch
from buildman.manager.ephemeral import EphemeralBuildManager
from buildman.jobutil.buildjob import BuildJob

class TestEphemeralBuildManager:
    @patch.object(BuildJob, 'send_notification')
    def test_build_start_notification(self, mock_send_notification):
        manager = EphemeralBuildManager()
        manager.update_job_phase(BuildJob(), 'BUILDING')
        mock_send_notification.assert_called_once_with('build_start')

    @patch.object(BuildJob, 'send_notification')
    def test_no_build_start_notification_for_other_phases(self, mock_send_notification):
        manager = EphemeralBuildManager()
        manager.update_job_phase(BuildJob(), 'BUILD_SCHEDULED')
        assert not mock_send_notification.called