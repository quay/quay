from test.fixtures import *

import pytest

from notifications.notificationevent import (
    BuildSuccessEvent,
    NotificationEvent,
    QuotaErrorEvent,
    QuotaWarningEvent,
    VulnerabilityFoundEvent,
)
from util.morecollections import AttrDict


@pytest.mark.parametrize("event_kind", NotificationEvent.event_names())
def test_create_notifications(event_kind):
    assert NotificationEvent.get_event(event_kind) is not None


@pytest.mark.parametrize("event_name", NotificationEvent.event_names())
def test_build_notification(event_name, initialized_db):
    # Create the notification event.
    found = NotificationEvent.get_event(event_name)
    sample_data = found.get_sample_data("foo", "bar", {"level": "low"})

    # Make sure all calls succeed.
    notification_data = {
        "performer_data": {},
    }

    found.get_level(sample_data, notification_data)
    found.get_summary(sample_data, notification_data)
    found.get_message(sample_data, notification_data)


def test_build_emptyjson():
    notification_data = AttrDict(
        {
            "event_config_dict": None,
        }
    )

    # No build data at all.
    assert BuildSuccessEvent().should_perform({}, notification_data)


def test_build_nofilter():
    notification_data = AttrDict(
        {
            "event_config_dict": {},
        }
    )

    # No build data at all.
    assert BuildSuccessEvent().should_perform({}, notification_data)

    # With trigger metadata but no ref.
    assert BuildSuccessEvent().should_perform(
        {
            "trigger_metadata": {},
        },
        notification_data,
    )

    # With trigger metadata and a ref.
    assert BuildSuccessEvent().should_perform(
        {
            "trigger_metadata": {
                "ref": "refs/heads/somebranch",
            },
        },
        notification_data,
    )


def test_build_emptyfilter():
    notification_data = AttrDict(
        {
            "event_config_dict": {"ref-regex": ""},
        }
    )

    # No build data at all.
    assert BuildSuccessEvent().should_perform({}, notification_data)

    # With trigger metadata but no ref.
    assert BuildSuccessEvent().should_perform(
        {
            "trigger_metadata": {},
        },
        notification_data,
    )

    # With trigger metadata and a ref.
    assert BuildSuccessEvent().should_perform(
        {
            "trigger_metadata": {
                "ref": "refs/heads/somebranch",
            },
        },
        notification_data,
    )


def test_build_invalidfilter():
    notification_data = AttrDict(
        {
            "event_config_dict": {"ref-regex": "]["},
        }
    )

    # No build data at all.
    assert not BuildSuccessEvent().should_perform({}, notification_data)

    # With trigger metadata but no ref.
    assert not BuildSuccessEvent().should_perform(
        {
            "trigger_metadata": {},
        },
        notification_data,
    )

    # With trigger metadata and a ref.
    assert not BuildSuccessEvent().should_perform(
        {
            "trigger_metadata": {
                "ref": "refs/heads/somebranch",
            },
        },
        notification_data,
    )


def test_build_withfilter():
    notification_data = AttrDict(
        {
            "event_config_dict": {"ref-regex": "refs/heads/master"},
        }
    )

    # No build data at all.
    assert not BuildSuccessEvent().should_perform({}, notification_data)

    # With trigger metadata but no ref.
    assert not BuildSuccessEvent().should_perform(
        {
            "trigger_metadata": {},
        },
        notification_data,
    )

    # With trigger metadata and a not-matching ref.
    assert not BuildSuccessEvent().should_perform(
        {
            "trigger_metadata": {
                "ref": "refs/heads/somebranch",
            },
        },
        notification_data,
    )

    # With trigger metadata and a matching ref.
    assert BuildSuccessEvent().should_perform(
        {
            "trigger_metadata": {
                "ref": "refs/heads/master",
            },
        },
        notification_data,
    )


def test_build_withwildcardfilter():
    notification_data = AttrDict(
        {
            "event_config_dict": {"ref-regex": "refs/heads/.+"},
        }
    )

    # No build data at all.
    assert not BuildSuccessEvent().should_perform({}, notification_data)

    # With trigger metadata but no ref.
    assert not BuildSuccessEvent().should_perform(
        {
            "trigger_metadata": {},
        },
        notification_data,
    )

    # With trigger metadata and a not-matching ref.
    assert not BuildSuccessEvent().should_perform(
        {
            "trigger_metadata": {
                "ref": "refs/tags/sometag",
            },
        },
        notification_data,
    )

    # With trigger metadata and a matching ref.
    assert BuildSuccessEvent().should_perform(
        {
            "trigger_metadata": {
                "ref": "refs/heads/master",
            },
        },
        notification_data,
    )

    # With trigger metadata and another matching ref.
    assert BuildSuccessEvent().should_perform(
        {
            "trigger_metadata": {
                "ref": "refs/heads/somebranch",
            },
        },
        notification_data,
    )


def test_vulnerability_notification_nolevel():
    notification_data = AttrDict(
        {
            "event_config_dict": {},
        }
    )

    # No level specified.
    assert VulnerabilityFoundEvent().should_perform({}, notification_data)


def test_vulnerability_notification_nopvulninfo():
    notification_data = AttrDict(
        {
            "event_config_dict": {"level": 3},
        }
    )

    # No vuln info.
    assert not VulnerabilityFoundEvent().should_perform({}, notification_data)


def test_vulnerability_notification_normal():
    notification_data = AttrDict(
        {
            "event_config_dict": {"level": 3},
        }
    )

    info = {"vulnerability": {"priority": "Critical"}}
    assert VulnerabilityFoundEvent().should_perform(info, notification_data)


class TestQuotaWarningEvent:
    def test_event_name(self):
        assert QuotaWarningEvent.event_name() == "quota_warning"

    def test_get_level(self):
        event = QuotaWarningEvent()
        assert event.get_level({}, {}) == "warning"

    def test_get_summary(self):
        event = QuotaWarningEvent()
        event_data = {"namespace": "testorg", "threshold_percent": 80}
        summary = event.get_summary(event_data, {})
        assert "testorg" in summary
        assert "80%" in summary

    def test_get_sample_data(self):
        event = QuotaWarningEvent()
        sample = event.get_sample_data("testorg", "testrepo", {})
        assert sample["namespace"] == "testorg"
        assert sample["threshold_percent"] == 80
        assert "usage_bytes" in sample
        assert "limit_bytes" in sample
        assert "usage_percent" in sample
        assert "homepage" in sample

    def test_should_perform_default_true(self):
        event = QuotaWarningEvent()
        assert event.should_perform({}, {})

    def test_lookup_via_event_name(self):
        found = NotificationEvent.get_event("quota_warning")
        assert isinstance(found, QuotaWarningEvent)


class TestQuotaErrorEvent:
    def test_event_name(self):
        assert QuotaErrorEvent.event_name() == "quota_error"

    def test_get_level(self):
        event = QuotaErrorEvent()
        assert event.get_level({}, {}) == "error"

    def test_get_summary(self):
        event = QuotaErrorEvent()
        event_data = {"namespace": "testorg", "usage_percent": 105}
        summary = event.get_summary(event_data, {})
        assert "testorg" in summary
        assert "105%" in summary

    def test_get_sample_data(self):
        event = QuotaErrorEvent()
        sample = event.get_sample_data("testorg", "testrepo", {})
        assert sample["namespace"] == "testorg"
        assert sample["threshold_percent"] == 100
        assert sample["usage_percent"] == 105
        assert "usage_bytes" in sample
        assert "limit_bytes" in sample
        assert "homepage" in sample

    def test_should_perform_default_true(self):
        event = QuotaErrorEvent()
        assert event.should_perform({}, {})

    def test_lookup_via_event_name(self):
        found = NotificationEvent.get_event("quota_error")
        assert isinstance(found, QuotaErrorEvent)
