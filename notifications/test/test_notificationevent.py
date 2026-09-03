import time

import pytest

import notifications.notificationevent as notificationevent
from notifications.notificationevent import (
    MAX_TAG_REGEX_LENGTH,
    PRODUCER_TAG_LIMIT,
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


def test_vulnerability_notification_no_tag_regex():
    # No tag-regex configured: fire regardless of tags (backward compatible).
    notification_data = AttrDict({"event_config_dict": {}})
    assert VulnerabilityFoundEvent().should_perform({"tags": ["v1.0"]}, notification_data)


def test_vulnerability_notification_matching_tag_regex():
    notification_data = AttrDict({"event_config_dict": {"tag-regex": "v2\\..*"}})
    assert VulnerabilityFoundEvent().should_perform({"tags": ["v1.0", "v2.0"]}, notification_data)


def test_vulnerability_notification_nonmatching_tag_regex():
    notification_data = AttrDict({"event_config_dict": {"tag-regex": "v2\\..*"}})
    assert not VulnerabilityFoundEvent().should_perform({"tags": ["v1.0"]}, notification_data)


def test_vulnerability_notification_empty_tags_with_regex():
    notification_data = AttrDict({"event_config_dict": {"tag-regex": "v2\\..*"}})
    assert not VulnerabilityFoundEvent().should_perform({"tags": []}, notification_data)
    assert not VulnerabilityFoundEvent().should_perform({}, notification_data)


def test_vulnerability_notification_invalid_tag_regex():
    notification_data = AttrDict({"event_config_dict": {"tag-regex": "]["}})
    assert not VulnerabilityFoundEvent().should_perform({"tags": ["v2.0"]}, notification_data)


def test_vulnerability_notification_tag_regex_and_level():
    notification_data = AttrDict({"event_config_dict": {"tag-regex": "v2\\..*", "level": 3}})

    # Tag matches and severity within level: fire.
    assert VulnerabilityFoundEvent().should_perform(
        {"tags": ["v2.0"], "vulnerability": {"priority": "Critical"}}, notification_data
    )

    # Tag matches but severity below the configured level: do not fire.
    assert not VulnerabilityFoundEvent().should_perform(
        {"tags": ["v2.0"], "vulnerability": {"priority": "Negligible"}}, notification_data
    )

    # Severity within level but no matching tag: do not fire.
    assert not VulnerabilityFoundEvent().should_perform(
        {"tags": ["v1.0"], "vulnerability": {"priority": "Critical"}}, notification_data
    )


def test_validate_event_config_accepts_valid_tag_regex():
    # A compilable, in-bounds pattern (and a blank/absent one) passes validation.
    VulnerabilityFoundEvent().validate_event_config({"tag-regex": "^prod-.+$"})
    VulnerabilityFoundEvent().validate_event_config({"tag-regex": ""})
    VulnerabilityFoundEvent().validate_event_config({})


def test_validate_event_config_rejects_uncompilable_tag_regex():
    with pytest.raises(InvalidNotificationEventConfigException):
        VulnerabilityFoundEvent().validate_event_config({"tag-regex": "]["})


def test_validate_event_config_rejects_too_long_tag_regex():
    long_pattern = "a" * (MAX_TAG_REGEX_LENGTH + 1)
    with pytest.raises(InvalidNotificationEventConfigException):
        VulnerabilityFoundEvent().validate_event_config({"tag-regex": long_pattern})


def test_vulnerability_notification_tag_regex_too_long():
    # A pattern beyond the length bound is rejected without attempting to match.
    long_pattern = "a" * (MAX_TAG_REGEX_LENGTH + 1)
    notification_data = AttrDict({"event_config_dict": {"tag-regex": long_pattern}})
    assert not VulnerabilityFoundEvent().should_perform({"tags": ["aaa"]}, notification_data)


def test_vulnerability_notification_tag_regex_redos_bounded():
    # A catastrophically-backtracking pattern against a long non-matching tag must not pin the
    # CPU: the per-tag timeout aborts evaluation and the event does not fire, quickly.
    notification_data = AttrDict({"event_config_dict": {"tag-regex": "^(a+)+$"}})
    evil_tag = "a" * 40 + "!"

    start = time.perf_counter()
    result = VulnerabilityFoundEvent().should_perform({"tags": [evil_tag]}, notification_data)
    elapsed = time.perf_counter() - start

    assert not result
    # Without the timeout this pattern runs for many seconds; allow generous headroom over the
    # 1.0s budget to stay stable in CI while still proving evaluation is bounded.
    assert elapsed < 10


def test_vulnerability_notification_tag_regex_whole_tag_match():
    # fullmatch semantics: a filter must match the whole tag, not just a prefix.
    notification_data = AttrDict({"event_config_dict": {"tag-regex": "latest"}})
    assert VulnerabilityFoundEvent().should_perform({"tags": ["latest"]}, notification_data)
    assert not VulnerabilityFoundEvent().should_perform(
        {"tags": ["latest-extra"]}, notification_data
    )


def test_vulnerability_notification_tag_regex_skips_digest():
    # Producers substitute the manifest digest for the tag list when a manifest has no tags. A
    # broad filter must not match the digest, since it is not a tag reference.
    notification_data = AttrDict({"event_config_dict": {"tag-regex": ".*"}})
    assert not VulnerabilityFoundEvent().should_perform(
        {"tags": ["sha256:" + "a" * 64]}, notification_data
    )


def test_vulnerability_notification_tag_regex_fails_open_at_producer_limit():
    # A non-matching tag list at the producer cap may have had a matching tag truncated away, so
    # the filter fails open and fires; just below the cap it does not.
    notification_data = AttrDict({"event_config_dict": {"tag-regex": "no-such-tag"}})

    at_limit = ["tag-%d" % i for i in range(PRODUCER_TAG_LIMIT)]
    assert len(at_limit) == PRODUCER_TAG_LIMIT
    assert VulnerabilityFoundEvent().should_perform({"tags": at_limit}, notification_data)

    below_limit = ["tag-%d" % i for i in range(PRODUCER_TAG_LIMIT - 1)]
    assert not VulnerabilityFoundEvent().should_perform({"tags": below_limit}, notification_data)


def test_validate_event_config_rejects_non_string_tag_regex():
    for bad in (123, ["["], {"x": "y"}):
        with pytest.raises(InvalidNotificationEventConfigException):
            VulnerabilityFoundEvent().validate_event_config({"tag-regex": bad})


def test_vulnerability_notification_non_string_tag_regex():
    # A non-string pattern reaching the matcher (e.g. a config persisted before validation was
    # added) is treated as no match rather than coerced.
    notification_data = AttrDict({"event_config_dict": {"tag-regex": 123}})
    assert not VulnerabilityFoundEvent().should_perform({"tags": ["123"]}, notification_data)


@pytest.mark.parametrize("bad", [0, False, [], {}])
def test_validate_event_config_rejects_falsey_non_string_tag_regex(bad):
    # Falsey non-strings (0, False, [], {}) must not be mistaken for "no filter": they are
    # rejected at creation time, just like any other non-string pattern.
    with pytest.raises(InvalidNotificationEventConfigException):
        VulnerabilityFoundEvent().validate_event_config({"tag-regex": bad})


@pytest.mark.parametrize("bad", [0, False, [], {}])
def test_vulnerability_notification_falsey_non_string_tag_regex(bad):
    # A falsey non-string filter persisted before validation must not disable filtering (which
    # would notify on every tag); it is treated as no match, so the event does not fire.
    notification_data = AttrDict({"event_config_dict": {"tag-regex": bad}})
    assert not VulnerabilityFoundEvent().should_perform({"tags": ["v1.0"]}, notification_data)


@pytest.mark.parametrize("empty", ["", None])
def test_vulnerability_notification_empty_tag_regex_fires(empty):
    # An empty string (the React form posts "" when the field is left blank) or an absent filter
    # means no filter is configured, so the event fires regardless of tags.
    notification_data = AttrDict({"event_config_dict": {"tag-regex": empty}})
    assert VulnerabilityFoundEvent().should_perform({"tags": ["v1.0"]}, notification_data)
    # Absent key behaves the same as an explicit empty value.
    assert VulnerabilityFoundEvent().should_perform(
        {"tags": ["v1.0"]}, AttrDict({"event_config_dict": {}})
    )


def test_vulnerability_notification_tag_regex_timeout(monkeypatch):
    # Deterministically exercise the timeout path: a catastrophically-backtracking pattern
    # against a long non-matching tag with a tiny per-tag budget must abort and not fire, without
    # raising.
    monkeypatch.setattr(notificationevent, "TAG_REGEX_MATCH_TIMEOUT", 0.000001)
    notification_data = AttrDict({"event_config_dict": {"tag-regex": "^(a+)+$"}})
    evil_tag = "a" * 10000 + "b"
    assert not VulnerabilityFoundEvent().should_perform({"tags": [evil_tag]}, notification_data)


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
