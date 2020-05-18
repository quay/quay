import base64
import logging
import fnmatch

from abc import ABCMeta, abstractmethod
from six import add_metaclass
from urllib.parse import urlparse

import requests

from data import database

from workers.repomirrorworker.rules import RepoMirrorComplexRuleType
from workers.repomirrorworker.skopeo_calls import lookup_manifest_digest


class ValidationFailureException(Exception):
    """ Exception raised if a rule fails to validate. """


@add_metaclass(ABCMeta)
class RuleHandler(object):
    """ Defines a handler for a particular kind of repo mirroring rule. """

    @abstractmethod
    def validate(self, rule_data):
        """ Validates the given rule data for this rule kind. Raises ValidationFailureException on failure. """

    @abstractmethod
    def describe(self, rule_data):
        """ Describes the given rule. """

    @abstractmethod
    def filter_tags(self, skopeo, mirror, rule_data, tags, verbose_logs):
        """ Runs the rule to filter the tags found in `tag`, yielded the updated set of tags. """

    @abstractmethod
    def list_direct_tag_references(self, rule_data):
        """ Returns the set of directly referenced tag names in the rule. Returns an iterable
            of some kind.
        """


class TagGlobCsvRule(RuleHandler):
    def validate(self, rule_data):
        if isinstance(rule_data, list):
            # NOTE: For legacy.
            return

        if not isinstance(rule_data.get("filter"), list):
            raise ValidationFailureException("Expected a list of tag globs as `filter`")

    def _filter_list(self, rule_data):
        if isinstance(rule_data, list):
            # NOTE: For legacy.
            return rule_data

        return rule_data["filter"]

    def describe(self, rule_data):
        return "Tag patterns: %s" % (",".join(self._filter_list(rule_data)))

    def filter_tags(self, skopeo, mirror, rule_data, tags, verbose_logs):
        matching_tags = []
        for pattern in self._filter_list(rule_data):
            matching_tags = matching_tags + list(
                filter(lambda tag: fnmatch.fnmatch(tag, pattern), tags)
            )
        return matching_tags

    def list_direct_tag_references(self, rule_data):
        for pattern in rule_data:
            if "*" not in pattern:
                yield pattern


class AndRule(RuleHandler):
    def validate(self, rule_data):
        if not rule_data.get("left"):
            raise ValidationFailureException("Missing left child")

        if not rule_data.get("right"):
            raise ValidationFailureException("Missing right child")

    def describe(self, rule_data):
        left_handler = get_handler(rule_data["left"])
        right_handler = get_handler(rule_data["right"])
        return "(%s) AND (%s)" % (
            left_handler.describe(rule_data["left"]),
            right_handler.describe(rule_data["right"]),
        )

    def filter_tags(self, skopeo, mirror, rule_data, tags, verbose_logs):
        left_handler = get_handler(rule_data["left"])
        right_handler = get_handler(rule_data["right"])

        left_tags = set(
            left_handler.filter_tags(skopeo, mirror, rule_data["left"], tags, verbose_logs)
        )
        right_tags = set(
            right_handler.filter_tags(skopeo, mirror, rule_data["right"], tags, verbose_logs)
        )
        return left_tags & right_tags

    def list_direct_tag_references(self, rule_data):
        left_handler = get_handler(rule_data["left"])
        right_handler = get_handler(rule_data["right"])
        return set(left_handler.list_direct_tag_references(rule_data["left"])) | set(
            left_handler.list_direct_tag_references(rule_data["right"])
        )


class OrRule(RuleHandler):
    def validate(self, rule_data):
        if not rule_data.get("left"):
            raise ValidationFailureException("Missing left child")

        if not rule_data.get("right"):
            raise ValidationFailureException("Missing right child")

    def describe(self, rule_data):
        left_handler = get_handler(rule_data["left"])
        right_handler = get_handler(rule_data["right"])
        return "(%s) OR (%s)" % (
            left_handler.describe(rule_data["left"]),
            right_handler.describe(rule_data["right"]),
        )

    def filter_tags(self, skopeo, mirror, rule_data, tags, verbose_logs):
        left_handler = get_handler(rule_data["left"])
        right_handler = get_handler(rule_data["right"])

        left_tags = set(
            left_handler.filter_tags(skopeo, mirror, rule_data["left"], tags, verbose_logs)
        )
        if left_tags & set(tags) == tags:
            return tags

        right_tags = set(
            right_handler.filter_tags(skopeo, mirror, rule_data["right"], tags, verbose_logs)
        )
        return left_tags | right_tags

    def list_direct_tag_references(self, rule_data):
        left_handler = get_handler(rule_data["left"])
        right_handler = get_handler(rule_data["right"])
        return set(left_handler.list_direct_tag_references(rule_data["left"])) | set(
            left_handler.list_direct_tag_references(rule_data["right"])
        )


class NotRule(RuleHandler):
    def validate(self, rule_data):
        if not rule_data.get("child"):
            raise ValidationFailureException("Missing child")

    def describe(self, rule_data):
        child_handler = get_handler(rule_data["child"])
        return "NOT (%s)" % (child_handler.describe(rule_data["child"]),)

    def filter_tags(self, skopeo, mirror, rule_data, tags, verbose_logs):
        child_handler = get_handler(rule_data["child"])
        child_tags = set(
            child_handler.filter_tags(skopeo, mirror, rule_data["child"], tags, verbose_logs)
        )
        return set(tags) - child_tags

    def list_direct_tag_references(self, rule_data):
        child_handler = get_handler(rule_data["child"])
        return child_handler.list_direct_tag_references(rule_data["child"])


class VulnerabilityFilterRule(RuleHandler):
    def validate(self, rule_data):
        if "allowed" not in rule_data:
            raise ValidationFailureException("Missing list of `allowed` severities")

        if not isinstance(rule_data["allowed"], list):
            raise ValidationFailureException("`allowed` must be a list of severities")

    def describe(self, rule_data):
        return "Has only *allowed* vulnerabilitiy severities: %s" % rule_data["allowed"]

    def filter_tags(self, skopeo, mirror, rule_data, tags, verbose_logs):
        # Lookup the .well-known from the registry server and make sure it supports the secscan
        # API.
        registry_server = urlparse("docker://%s" % mirror.external_reference).netloc
        assert registry_server, "Found empty registry server for reference `%s`: %s" % (
            mirror.external_reference,
            registry_server,
        )
        logger.debug("Checking registry server for security status: %s", registry_server)

        resp = requests.get("https://%s/.well-known/app-capabilities" % registry_server, timeout=10)
        if resp.status_code != 200:
            logger.debug(
                "Got non-200 for registry server %s for app-capabilities: %s",
                registry_server,
                resp.status_code,
            )
            raise StopIteration()

        capabilities = resp.json().get("capabilities")
        if capabilities is None:
            logger.debug(
                "Found no capabilities for registry server %s: %s", registry_server, resp.json()
            )
            raise StopIteration()

        logger.debug("Found capabilities for registry server %s: %s", registry_server, resp.json())
        secscan = capabilities.get("io.quay.manifest-security")
        if secscan is None:
            raise StopIteration()

        template = secscan.get("rest-api-template")
        if template is None:
            raise StopIteration()

        namespace_name, reponame = mirror.external_reference[len(registry_server) + 1 :].split(
            "/", 1
        )
        for tag in tags:
            digest = lookup_manifest_digest(skopeo, mirror, tag, verbose_logs=verbose_logs)

            # Retrieve the vulnerability information for the tag.
            url = template.format(namespace=namespace_name, reponame=reponame, digest=digest)
            if mirror.external_registry_username is not None:
                headers = {
                    "Authorization": "Basic %s"
                    % (
                        base64.b64encode(
                            "%s:%s"
                            % (
                                mirror.external_registry_username.decrypt(),
                                mirror.external_registry_password.decrypt(),
                            )
                        )
                    )
                }
            else:
                headers = {}

            secscan_info = requests.get(url, timeout=10, headers=headers)
            if secscan_info.status_code != 200:
                logger.debug(
                    "Got non-200 for sec scan info for tag `%s`: %s", url, secscan_info.status_code
                )
                continue

            severities_found = set()
            for feature in secscan_info.json().get("data", {}).get("Layer", {}).get("Features", []):
                for vuln in feature.get("Vulnerabilities", []):
                    severities_found.add(vuln.get("Severity") or "Unknown")

            logger.debug("Found severities for tag `%s`: %s", tag, severities_found)
            if not severities_found:
                yield tag
                continue

            if severities_found & set(rule.rule_value["allowed"]):
                yield tag
                continue

    def list_direct_tag_references(self, rule_data):
        return []


HANDLER_CLASSES = {
    RepoMirrorComplexRuleType.TAG_GLOB_CSV: TagGlobCsvRule,
    RepoMirrorComplexRuleType.AND: AndRule,
    RepoMirrorComplexRuleType.OR: OrRule,
    RepoMirrorComplexRuleType.NOT: NotRule,
    RepoMirrorComplexRuleType.ALLOWED_VULNERABILITY_SEVERITIES: VulnerabilityFilterRule,
}


def get_handler(rule_data, kind=None):
    """ Returns the handler for the given rule data, or the given kind if provided.
        Note that the data is immediately validated as well, so this can raise a
        ValidationFailureException.
    """
    kind = kind or rule_data["kind"]
    found = HANDLER_CLASSES[RepoMirrorComplexRuleType(kind)]()
    found.validate(rule_data)
    return found


def handler_for_mirroring_row(row):
    """ Returns the validated handler for the given mirroring row. """
    # NOTE: This check is for legacy rows.
    if row.rule_type == database.RepoMirrorRuleType.TAG_GLOB_CSV:
        return get_handler(row.rule_value, RepoMirrorComplexRuleType.TAG_GLOB_CSV)

    assert row.rule_type == database.RepoMirrorRuleType.COMPLEX
    return get_handler(row.rule_value)
