import logging
import re
import time
from datetime import datetime
from functools import lru_cache

import regex
from regex import Pattern

from notifications import build_namespace_event_data, build_repository_event_data
from util.jinjautil import get_template_env
from util.secscan import PRIORITY_LEVELS, get_priority_for_index

logger = logging.getLogger(__name__)

TEMPLATE_ENV = get_template_env("events")

# Upper bound on a configured vulnerability tag-filter pattern, mirroring the immutability
# policy limit. A legitimate filter never needs to be larger, and bounding it reduces the
# surface for catastrophic backtracking.
MAX_TAG_REGEX_LENGTH = 256

# Per-tag evaluation budget, in seconds, for the vulnerability tag filter. The `regex`
# module aborts a match that exceeds this, protecting the notification worker from a crafted
# ReDoS pattern (e.g. "^(a+)+$") that would otherwise pin CPU on a long non-matching tag.
TAG_REGEX_MATCH_TIMEOUT = 1.0

# Mirrors the TAG_LIMIT the notification producers apply when calling
# tag_names_for_manifest (workers/securityscanningnotificationworker.py and
# data/secscan_model/secscan_v4_model*.py). When a manifest carries more referencing tags than
# this, the producer truncates the list before it reaches the filter, so a matching tag beyond
# the cap would be invisible here. Kept as a local copy to avoid importing the worker/secscan
# modules (which would create an import cycle); it must stay in sync with those producers.
PRODUCER_TAG_LIMIT = 100


@lru_cache(maxsize=256)
def _compile_tag_regex(pattern: str) -> Pattern[str]:
    return regex.compile(pattern)


class InvalidNotificationEventException(Exception):
    pass


class InvalidNotificationEventConfigException(Exception):
    """Raised when a notification's event config fails validation at creation time."""

    pass


class NotificationEvent(object):
    def __init__(self):
        pass

    def get_level(self, event_data, notification_data):
        """
        Returns a 'level' representing the severity of the event.

        Valid values are: 'info', 'warning', 'error', 'primary', 'success'
        """
        raise NotImplementedError

    def get_summary(self, event_data, notification_data):
        """
        Returns a human readable one-line summary for the given notification data.
        """
        raise NotImplementedError

    def get_message(self, event_data, notification_data):
        """
        Returns a human readable HTML message for the given notification data.
        """
        return TEMPLATE_ENV.get_template(self.event_name() + ".html").render(
            {"event_data": event_data, "notification_data": notification_data}
        )

    def get_sample_data(self, namespace_name, repo_name, event_config):
        """
        Returns sample data for testing the raising of this notification, with an example
        notification.
        """
        raise NotImplementedError

    def should_perform(self, event_data, notification_data):
        """
        Whether a notification for this event should be performed.

        By default returns True.
        """
        return True

    def validate_event_config(self, event_config):
        """
        Validates the event-specific config supplied when creating a notification.

        Called at notification-creation time so that invalid config is rejected with an API
        validation error rather than silently breaking the notification when it later fires.
        Subclasses raise InvalidNotificationEventConfigException for invalid config. By default
        there is nothing to validate.
        """
        pass

    @classmethod
    def event_name(cls):
        """
        Particular event implemented by subclasses.
        """
        raise NotImplementedError

    @classmethod
    def get_event(cls, eventname):
        found = NotificationEvent._get_event(cls, eventname)
        if found is not None:
            return found

        raise InvalidNotificationEventException("Unable to find event: %s" % eventname)

    @classmethod
    def event_names(cls):
        for subc in cls.__subclasses__():
            if subc.event_name() is None:
                for subsubc in subc.__subclasses__():
                    yield subsubc.event_name()
            else:
                yield subc.event_name()

    @staticmethod
    def _get_event(cls, eventname):
        for subc in cls.__subclasses__():
            if subc.event_name() is None:
                found = NotificationEvent._get_event(subc, eventname)
                if found is not None:
                    return found
            elif subc.event_name() == eventname:
                return subc()


class RepoPushEvent(NotificationEvent):
    @classmethod
    def event_name(cls):
        return "repo_push"

    def get_level(self, event_data, notification_data):
        return "primary"

    def get_summary(self, event_data, notification_data):
        return "Repository %s updated" % (event_data["repository"])

    def get_sample_data(self, namespace_name, repo_name, event_config):
        return build_repository_event_data(
            namespace_name, repo_name, {"updated_tags": ["latest", "foo"], "pruned_image_count": 3}
        )


class RepoMirrorSyncStartedEvent(NotificationEvent):
    @classmethod
    def event_name(cls):
        return "repo_mirror_sync_started"

    def get_level(self, event_data, notification_data):
        return "info"

    def get_summary(self, event_data, notification_data):
        return "Repository Mirror started for %s" % (event_data["message"])

    def get_sample_data(self, namespace_name, repo_name, event_config):
        return build_repository_event_data(
            namespace_name, repo_name, {"message": "TEST NOTIFICATION"}
        )


class RepoMirrorSyncSuccessEvent(NotificationEvent):
    @classmethod
    def event_name(cls):
        return "repo_mirror_sync_success"

    def get_level(self, event_data, notification_data):
        return "success"

    def get_summary(self, event_data, notification_data):
        return "Repository Mirror success for %s" % (event_data["message"])

    def get_sample_data(self, namespace_name, repo_name, event_config):
        return build_repository_event_data(
            namespace_name, repo_name, {"message": "TEST NOTIFICATION"}
        )


class RepoMirrorSyncFailedEvent(NotificationEvent):
    @classmethod
    def event_name(cls):
        return "repo_mirror_sync_failed"

    def get_level(self, event_data, notification_data):
        return "error"

    def get_summary(self, event_data, notification_data):
        return "Repository Mirror failed for %s" % (event_data["message"])

    def get_sample_data(self, namespace_name, repo_name, event_config):
        return build_repository_event_data(
            namespace_name, repo_name, {"message": "TEST NOTIFICATION"}
        )


def _build_summary(event_data):
    """
    Returns a summary string for the build data found in the event data block.
    """
    summary = "for repository %s [%s]" % (event_data["repository"], event_data["build_id"][0:7])
    return summary


class VulnerabilityFoundEvent(NotificationEvent):
    CONFIG_LEVEL = "level"
    CONFIG_TAG_REGEX = "tag-regex"
    PRIORITY_KEY = "priority"
    VULNERABILITY_KEY = "vulnerability"
    MULTIPLE_VULNERABILITY_KEY = "vulnerabilities"
    VULNERABLE_INDEX_REPORT_CREATED = "vulnerable_index_report_created"

    @classmethod
    def event_name(cls):
        return "vulnerability_found"

    def get_level(self, event_data, notification_data):
        vuln_data = event_data[VulnerabilityFoundEvent.VULNERABILITY_KEY]
        priority = vuln_data[VulnerabilityFoundEvent.PRIORITY_KEY]
        if priority == "Critical":
            return "error"

        if priority == "Medium" or priority == "High":
            return "warning"

        return "info"

    def get_sample_data(self, namespace_name, repo_name, event_config):
        level = event_config.get(VulnerabilityFoundEvent.CONFIG_LEVEL, "Critical")
        return build_repository_event_data(
            namespace_name,
            repo_name,
            {
                "tags": ["latest", "prod", "foo", "bar", "baz"],
                "image": "some-image-id",
                "vulnerability": {
                    "id": "CVE-FAKE-CVE",
                    "description": "A futurist vulnerability",
                    "link": "https://security-tracker.debian.org/tracker/CVE-FAKE-CVE",
                    "priority": get_priority_for_index(level),
                },
            },
        )

    def validate_event_config(self, event_config):
        # Validate the optional tag filter up front so a bad pattern is rejected with an API
        # error at creation time, instead of silently suppressing every notification when it
        # later fails to compile or is refused for being too long at match time.
        tag_regex = event_config.get(VulnerabilityFoundEvent.CONFIG_TAG_REGEX) or None
        if tag_regex is None:
            return

        # Require a string. Without this, a non-string value (e.g. 123, ["["], {"x": "y"}) would
        # be coerced with str() and stored as a "regex" that can never behave as the caller
        # intended.
        if not isinstance(tag_regex, str):
            raise InvalidNotificationEventConfigException(
                "Tag filter regular expression must be a string"
            )

        pattern = tag_regex
        if len(pattern) > MAX_TAG_REGEX_LENGTH:
            raise InvalidNotificationEventConfigException(
                "Tag filter regular expression exceeds the maximum length of %d characters"
                % MAX_TAG_REGEX_LENGTH
            )

        try:
            _compile_tag_regex(pattern)
        except regex.error as ex:
            raise InvalidNotificationEventConfigException(
                "Invalid tag filter regular expression: %s" % ex
            )

    def _matches_tag_filter(self, event_data, tag_regex):
        # A non-string pattern cannot be a valid regex (validate_event_config now rejects one at
        # creation time, but a config persisted before that check, or reached via another path,
        # could still carry one). Treat it as no match rather than coercing it with str().
        if not isinstance(tag_regex, str):
            logger.warning(
                "Vulnerability event tag filter is not a string (%s); not firing event",
                type(tag_regex).__name__,
            )
            return False

        # Reject overly long patterns outright: they only add to matching cost and a
        # legitimate tag filter never needs to be this large.
        pattern = tag_regex
        if len(pattern) > MAX_TAG_REGEX_LENGTH:
            logger.warning(
                "Vulnerability event tag filter pattern exceeds %d characters; not firing event",
                MAX_TAG_REGEX_LENGTH,
            )
            return False

        # Try parsing the regex string as a regular expression. If we fail, we fail to fire
        # the event.
        try:
            matcher = _compile_tag_regex(pattern)
        except regex.error:
            logger.warning("Regular expression error for vulnerability event filter: %s", pattern)
            return False

        # Only fire the event if at least one referencing tag matches the pattern as a whole.
        # We use fullmatch (not match, which anchors only at the start, so "latest" would match
        # "latest-extra") to keep the filter consistent with immutability tag patterns and the
        # UI placeholder "(v2\..*)|(latest)", which imply whole-tag matching. An empty tag list
        # (or no tags at all) never matches. Matching runs under a per-tag timeout so a crafted,
        # catastrophically-backtracking pattern cannot exhaust worker CPU (ReDoS); on timeout we
        # conservatively treat the tag as non-matching.
        tags = event_data.get("tags", [])
        for tag in tags:
            # Producers substitute the manifest digest (e.g. "sha256:...") for the tag list when
            # a manifest has no referencing tags. A digest is not a tag reference, and the UI
            # promises matching against tag(s), so it must never satisfy the filter. Per the
            # Docker tag grammar ([A-Za-z0-9_][A-Za-z0-9_.-]{0,127}) a tag can never contain a
            # colon, so any entry with one is a digest (or otherwise not a tag) and is skipped.
            if not isinstance(tag, str) or ":" in tag:
                continue
            try:
                if matcher.fullmatch(tag, timeout=TAG_REGEX_MATCH_TIMEOUT):
                    return True
            except TimeoutError:
                logger.warning(
                    "Regex match timed out for vulnerability event filter pattern %s against tag %s",
                    pattern,
                    tag,
                )

        # Fail open on truncation. The producers cap the referencing tags at PRODUCER_TAG_LIMIT,
        # so when the delivered list is at (or above) that cap a matching tag may have been
        # dropped before it reached us. Silently suppressing a security notification is worse
        # than a possible false positive, so in that case we fire anyway.
        if len(tags) >= PRODUCER_TAG_LIMIT:
            logger.warning(
                "Vulnerability event tag filter %s matched none of %d tags, at or above the "
                "producer tag limit of %d; firing anyway to avoid suppressing a security "
                "notification whose matching tag may have been truncated",
                pattern,
                len(tags),
                PRODUCER_TAG_LIMIT,
            )
            return True

        return False

    def should_perform(self, event_data, notification_data):
        event_config = notification_data.event_config_dict

        # Filter on the referencing tags, if a tag pattern is configured. This is independent
        # of the severity level filter below; when both are set, both must pass.
        tag_regex = event_config.get(VulnerabilityFoundEvent.CONFIG_TAG_REGEX) or None
        if tag_regex is not None and not self._matches_tag_filter(event_data, tag_regex):
            return False

        if VulnerabilityFoundEvent.CONFIG_LEVEL not in event_config:
            return True

        if VulnerabilityFoundEvent.VULNERABLE_INDEX_REPORT_CREATED in event_data:
            return True

        if VulnerabilityFoundEvent.VULNERABILITY_KEY not in event_data:
            return False

        vuln_info = event_data.get(VulnerabilityFoundEvent.VULNERABILITY_KEY, {})
        event_severity = PRIORITY_LEVELS.get(vuln_info.get("priority", "Unknown"))
        if event_severity is None:
            return False

        actual_level_index = int(event_severity["index"])
        filter_level_index = int(event_config[VulnerabilityFoundEvent.CONFIG_LEVEL])
        return actual_level_index <= filter_level_index

    def get_summary(self, event_data, notification_data):
        vuln_key = VulnerabilityFoundEvent.VULNERABILITY_KEY
        priority_key = VulnerabilityFoundEvent.PRIORITY_KEY

        multiple_vulns = event_data.get(VulnerabilityFoundEvent.MULTIPLE_VULNERABILITY_KEY)
        if multiple_vulns is not None:
            top_priority = multiple_vulns[0].get(priority_key, "Unknown")
            matching = [v for v in multiple_vulns if v.get(priority_key, "Unknown") == top_priority]

            msg = "%s %s" % (len(matching), top_priority)
            if len(matching) < len(multiple_vulns):
                msg += " and %s more" % (len(multiple_vulns) - len(matching))

            msg += " vulnerabilities were detected in repository %s in %s tags"
            return msg % (event_data["repository"], len(event_data["tags"]))
        else:
            msg = "%s vulnerability detected in repository %s in %s tags"
            return msg % (
                event_data[vuln_key][priority_key],
                event_data["repository"],
                len(event_data["tags"]),
            )


class BaseBuildEvent(NotificationEvent):
    @classmethod
    def event_name(cls):
        return None

    def should_perform(self, event_data, notification_data):
        if not notification_data.event_config_dict:
            return True

        event_config = notification_data.event_config_dict
        ref_regex = event_config.get("ref-regex") or None
        if ref_regex is None:
            return True

        # Lookup the ref. If none, this is a non-git build and we should not fire the event.
        ref = event_data.get("trigger_metadata", {}).get("ref", None)
        if ref is None:
            return False

        # Try parsing the regex string as a regular expression. If we fail, we fail to fire
        # the event.
        try:
            return bool(re.compile(str(ref_regex)).match(ref))
        except Exception:
            logger.warning("Regular expression error for build event filter: %s", ref_regex)
            return False


class BuildQueueEvent(BaseBuildEvent):
    @classmethod
    def event_name(cls):
        return "build_queued"

    def get_level(self, event_data, notification_data):
        return "info"

    def get_sample_data(self, namespace_name, repo_name, event_config):
        build_uuid = "fake-build-id"
        return build_repository_event_data(
            namespace_name,
            repo_name,
            {
                "is_manual": False,
                "build_id": build_uuid,
                "build_name": "some-fake-build",
                "docker_tags": ["latest", "foo", "bar"],
                "trigger_id": "1245634",
                "trigger_kind": "GitHub",
                "trigger_metadata": {
                    "default_branch": "master",
                    "ref": "refs/heads/somebranch",
                    "commit": "42d4a62c53350993ea41069e9f2cfdefb0df097d",
                    "commit_info": {
                        "url": "http://path/to/the/commit",
                        "message": "Some commit message",
                        "date": time.mktime(datetime.now().timetuple()),
                        "author": {
                            "username": "fakeauthor",
                            "url": "http://path/to/fake/author/in/scm",
                            "avatar_url": "http://www.gravatar.com/avatar/fakehash",
                        },
                    },
                },
            },
            subpage="/build/%s" % build_uuid,
        )

    def get_summary(self, event_data, notification_data):
        return "Build queued " + _build_summary(event_data)


class BuildStartEvent(BaseBuildEvent):
    @classmethod
    def event_name(cls):
        return "build_start"

    def get_level(self, event_data, notification_data):
        return "info"

    def get_sample_data(self, namespace_name, repo_name, event_config):
        build_uuid = "fake-build-id"
        return build_repository_event_data(
            namespace_name,
            repo_name,
            {
                "build_id": build_uuid,
                "build_name": "some-fake-build",
                "docker_tags": ["latest", "foo", "bar"],
                "trigger_id": "1245634",
                "trigger_kind": "GitHub",
                "trigger_metadata": {
                    "default_branch": "master",
                    "ref": "refs/heads/somebranch",
                    "commit": "42d4a62c53350993ea41069e9f2cfdefb0df097d",
                },
            },
            subpage="/build/%s" % build_uuid,
        )

    def get_summary(self, event_data, notification_data):
        return "Build started " + _build_summary(event_data)


class BuildSuccessEvent(BaseBuildEvent):
    @classmethod
    def event_name(cls):
        return "build_success"

    def get_level(self, event_data, notification_data):
        return "success"

    def get_sample_data(self, namespace_name, repo_name, event_config):
        build_uuid = "fake-build-id"
        return build_repository_event_data(
            namespace_name,
            repo_name,
            {
                "build_id": build_uuid,
                "build_name": "some-fake-build",
                "docker_tags": ["latest", "foo", "bar"],
                "trigger_id": "1245634",
                "trigger_kind": "GitHub",
                "trigger_metadata": {
                    "default_branch": "master",
                    "ref": "refs/heads/somebranch",
                    "commit": "42d4a62c53350993ea41069e9f2cfdefb0df097d",
                },
                "image_id": "1245657346",
            },
            subpage="/build/%s" % build_uuid,
        )

    def get_summary(self, event_data, notification_data):
        return "Build succeeded " + _build_summary(event_data)


class BuildFailureEvent(BaseBuildEvent):
    @classmethod
    def event_name(cls):
        return "build_failure"

    def get_level(self, event_data, notification_data):
        return "error"

    def get_sample_data(self, namespace_name, repo_name, event_config):
        build_uuid = "fake-build-id"
        return build_repository_event_data(
            namespace_name,
            repo_name,
            {
                "build_id": build_uuid,
                "build_name": "some-fake-build",
                "docker_tags": ["latest", "foo", "bar"],
                "trigger_kind": "GitHub",
                "error_message": "This is a fake error message",
                "trigger_id": "1245634",
                "trigger_kind": "GitHub",
                "trigger_metadata": {
                    "default_branch": "master",
                    "ref": "refs/heads/somebranch",
                    "commit": "42d4a62c53350993ea41069e9f2cfdefb0df097d",
                    "commit_info": {
                        "url": "http://path/to/the/commit",
                        "message": "Some commit message",
                        "date": time.mktime(datetime.now().timetuple()),
                        "author": {
                            "username": "fakeauthor",
                            "url": "http://path/to/fake/author/in/scm",
                            "avatar_url": "http://www.gravatar.com/avatar/fakehash",
                        },
                    },
                },
            },
            subpage="/build/%s" % build_uuid,
        )

    def get_summary(self, event_data, notification_data):
        return "Build failure " + _build_summary(event_data)


class BuildCancelledEvent(BaseBuildEvent):
    @classmethod
    def event_name(cls):
        return "build_cancelled"

    def get_level(self, event_data, notification_data):
        return "info"

    def get_sample_data(self, namespace_name, repo_name, event_config):
        build_uuid = "fake-build-id"
        return build_repository_event_data(
            namespace_name,
            repo_name,
            {
                "build_id": build_uuid,
                "build_name": "some-fake-build",
                "docker_tags": ["latest", "foo", "bar"],
                "trigger_id": "1245634",
                "trigger_kind": "GitHub",
                "trigger_metadata": {
                    "default_branch": "master",
                    "ref": "refs/heads/somebranch",
                    "commit": "42d4a62c53350993ea41069e9f2cfdefb0df097d",
                },
                "image_id": "1245657346",
            },
            subpage="/build/%s" % build_uuid,
        )

    def get_summary(self, event_data, notification_data):
        return "Build cancelled " + _build_summary(event_data)


class RepoImageExpiryEvent(NotificationEvent):
    @classmethod
    def event_name(cls):
        return "repo_image_expiry"

    def get_level(self, event_data, notification_data):
        return "info"

    def get_summary(self, event_data, notification_data):
        return f"Repository {event_data['repository']} image(s) expiring"

    def get_sample_data(self, namespace_name, repo_name, event_config):
        return build_repository_event_data(
            namespace_name,
            repo_name,
            {"tags": ["latest", "v1"], "expiring_in": f"{event_config.get('days', None)} days"},
        )


class QuotaWarningEvent(NotificationEvent):
    @classmethod
    def event_name(cls):
        return "quota_warning"

    def get_level(self, event_data, notification_data):
        return "warning"

    def get_summary(self, event_data, notification_data):
        return "Namespace %s storage usage has reached %s%% of its quota limit" % (
            event_data["namespace"],
            event_data["threshold_percent"],
        )

    def get_sample_data(self, namespace_name, repo_name, event_config):
        return build_namespace_event_data(
            namespace_name,
            {
                "threshold_percent": 80,
                "usage_bytes": 858993459,
                "limit_bytes": 1073741824,
                "usage_percent": 80,
                "usage_bytes_formatted": "819.20 MB",
                "limit_bytes_formatted": "1.00 GB",
            },
        )


class QuotaErrorEvent(NotificationEvent):
    @classmethod
    def event_name(cls):
        return "quota_error"

    def get_level(self, event_data, notification_data):
        return "error"

    def get_summary(self, event_data, notification_data):
        return "Namespace %s storage usage has exceeded its quota limit (%s%%)" % (
            event_data["namespace"],
            event_data["usage_percent"],
        )

    def get_sample_data(self, namespace_name, repo_name, event_config):
        return build_namespace_event_data(
            namespace_name,
            {
                "threshold_percent": 100,
                "usage_bytes": 1127428915,
                "limit_bytes": 1073741824,
                "usage_percent": 105,
                "usage_bytes_formatted": "1.05 GB",
                "limit_bytes_formatted": "1.00 GB",
            },
        )
