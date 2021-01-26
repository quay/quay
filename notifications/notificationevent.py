import logging
import time
import re

from datetime import datetime
from notifications import build_repository_event_data
from util.jinjautil import get_template_env
from util.secscan import PRIORITY_LEVELS, get_priority_for_index

logger = logging.getLogger(__name__)

TEMPLATE_ENV = get_template_env("events")


class InvalidNotificationEventException(Exception):
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
    PRIORITY_KEY = "priority"
    VULNERABILITY_KEY = "vulnerability"
    MULTIPLE_VULNERABILITY_KEY = "vulnerabilities"

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

    def should_perform(self, event_data, notification_data):
        event_config = notification_data.event_config_dict
        if VulnerabilityFoundEvent.CONFIG_LEVEL not in event_config:
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
