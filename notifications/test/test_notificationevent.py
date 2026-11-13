import pytest

from notifications.notificationevent import (
    BuildSuccessEvent,
    InvalidNotificationEventConfigException,
    NotificationEvent,
    QuotaErrorEvent,
    QuotaWarningEvent,
    VulnerabilityFoundEvent,
)
from test.fixtures import *
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


def vulnerability_notification_data(event_config):
    return AttrDict({"event_config_dict": event_config})


def test_vulnerability_notification_nolevel():
    assert VulnerabilityFoundEvent().should_perform({}, vulnerability_notification_data({}))


def test_vulnerability_notification_nopvulninfo():
    assert not VulnerabilityFoundEvent().should_perform(
        {}, vulnerability_notification_data({"level": 3})
    )


def test_vulnerability_notification_normal():
    info = {"vulnerability": {"priority": "Critical"}}
    assert VulnerabilityFoundEvent().should_perform(
        info, vulnerability_notification_data({"level": 3})
    )


@pytest.mark.parametrize("tag_regex", [None, "", "   "])
def test_vulnerability_notification_empty_tag_filter(tag_regex):
    info = {"tags": ["v1.0"], "vulnerability": {"priority": "Critical"}}
    assert VulnerabilityFoundEvent().should_perform(
        info, vulnerability_notification_data({"tag-regex": tag_regex})
    )


@pytest.mark.parametrize("tag", ["v2.0", "release-v2.0", "test-v2-build"])
def test_vulnerability_notification_tag_filter_searches_anywhere(tag):
    info = {"tags": [tag], "vulnerability": {"priority": "Critical"}}
    assert VulnerabilityFoundEvent().should_perform(
        info, vulnerability_notification_data({"tag-regex": "v2"})
    )


def test_vulnerability_notification_tag_filter_is_case_sensitive():
    info = {"tags": ["Release-v2.0"], "vulnerability": {"priority": "Critical"}}
    assert not VulnerabilityFoundEvent().should_perform(
        info, vulnerability_notification_data({"tag-regex": "release"})
    )


def test_vulnerability_notification_tag_filter_matches_any_tag():
    info = {
        "tags": ["v1.0", "release-v2.0", "latest"],
        "vulnerability": {"priority": "Critical"},
    }
    assert VulnerabilityFoundEvent().should_perform(
        info, vulnerability_notification_data({"tag-regex": "v2"})
    )


@pytest.mark.parametrize(
    "tags",
    [
        ["v1.0", "latest"],
        [],
        None,
        ["sha256:abcdef1234567890"],
    ],
)
def test_vulnerability_notification_tag_filter_without_matching_tag(tags):
    info = {"vulnerability": {"priority": "Critical"}}
    if tags is not None:
        info["tags"] = tags

    assert not VulnerabilityFoundEvent().should_perform(
        info, vulnerability_notification_data({"tag-regex": "v2"})
    )


def test_vulnerability_notification_tag_filter_applies_to_initial_report():
    info = {
        "tags": ["v1.0"],
        "vulnerable_index_report_created": "true",
        "vulnerability": {"priority": "Critical"},
    }
    assert not VulnerabilityFoundEvent().should_perform(
        info,
        vulnerability_notification_data({"level": 0, "tag-regex": "v2"}),
    )


def test_vulnerability_notification_matching_initial_report_preserves_severity_shortcut():
    info = {
        "tags": ["v2.0"],
        "vulnerable_index_report_created": "true",
        "vulnerability": {"priority": "Medium"},
    }
    assert VulnerabilityFoundEvent().should_perform(
        info,
        vulnerability_notification_data({"level": 0, "tag-regex": "v2"}),
    )


def test_vulnerability_notification_requires_severity_and_tag_to_match():
    info = {"tags": ["v2.0"], "vulnerability": {"priority": "Medium"}}
    assert not VulnerabilityFoundEvent().should_perform(
        info,
        vulnerability_notification_data({"level": 1, "tag-regex": "v2"}),
    )


def test_vulnerability_notification_matching_severity_and_tag():
    info = {"tags": ["v2.0"], "vulnerability": {"priority": "High"}}
    assert VulnerabilityFoundEvent().should_perform(
        info,
        vulnerability_notification_data({"level": 1, "tag-regex": "v2"}),
    )


def test_vulnerability_notification_invalid_stored_tag_filter(caplog):
    info = {"tags": ["v2.0"], "vulnerability": {"priority": "Critical"}}
    assert not VulnerabilityFoundEvent().should_perform(
        info, vulnerability_notification_data({"tag-regex": "[v2"})
    )
    assert "Regular expression error for vulnerability tag filter" in caplog.text


def test_vulnerability_notification_tag_filter_timeout_fails_closed(monkeypatch, caplog):
    class TimedOutRegex:
        def search(self, tag, timeout):
            raise TimeoutError

    monkeypatch.setattr(
        "notifications.notificationevent.regex.compile", lambda pattern: TimedOutRegex()
    )

    info = {"tags": ["v2.0"], "vulnerability": {"priority": "Critical"}}
    assert not VulnerabilityFoundEvent().should_perform(
        info, vulnerability_notification_data({"tag-regex": "v2"})
    )
    assert "Vulnerability tag regular expression timed out" in caplog.text


@pytest.mark.parametrize("event_config", [{"tag-regex": None}, {"tag-regex": ""}, {}])
def test_vulnerability_notification_validates_empty_tag_filter(event_config):
    VulnerabilityFoundEvent().validate_config(event_config)


@pytest.mark.parametrize("tag_regex", ["v2", "^v2\\.", "v1|v2"])
def test_vulnerability_notification_validates_tag_filter(tag_regex):
    VulnerabilityFoundEvent().validate_config({"tag-regex": tag_regex})


@pytest.mark.parametrize("tag_regex", [123, "[v2"])
def test_vulnerability_notification_rejects_invalid_tag_filter(tag_regex):
    with pytest.raises(InvalidNotificationEventConfigException):
        VulnerabilityFoundEvent().validate_config({"tag-regex": tag_regex})


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

    def test_get_sample_data_includes_formatted_bytes(self):
        event = QuotaWarningEvent()
        sample = event.get_sample_data("testorg", "testrepo", {})
        assert "usage_bytes_formatted" in sample
        assert "limit_bytes_formatted" in sample
        assert sample["usage_bytes_formatted"] == "819.20 MB"
        assert sample["limit_bytes_formatted"] == "1.00 GB"

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

    def test_get_sample_data_includes_formatted_bytes(self):
        event = QuotaErrorEvent()
        sample = event.get_sample_data("testorg", "testrepo", {})
        assert "usage_bytes_formatted" in sample
        assert "limit_bytes_formatted" in sample
        assert sample["usage_bytes_formatted"] == "1.05 GB"
        assert sample["limit_bytes_formatted"] == "1.00 GB"

    def test_should_perform_default_true(self):
        event = QuotaErrorEvent()
        assert event.should_perform({}, {})

    def test_lookup_via_event_name(self):
        found = NotificationEvent.get_event("quota_error")
        assert isinstance(found, QuotaErrorEvent)
