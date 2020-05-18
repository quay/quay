import os
import re

from app import app
from data import database


class RepoMirrorSkopeoException(Exception):
    """
    Exception raised if any calls to skopeo have failde.
    """

    def __init__(self, message, stdout, stderr):
        self.message = message
        self.stdout = stdout
        self.stderr = stderr


def get_all_tags(skopeo, mirror, expected_tags, verbose_logs=False):
    """ Looks up all tags found in the repository. """
    username, password = _credentials(mirror)

    with database.CloseForLongOperation(app.config):
        result = skopeo.tags(
            "docker://%s" % (mirror.external_reference),
            expected_tags=expected_tags,
            username=username,
            password=password,
            verbose_logs=verbose_logs,
            verify_tls=mirror.external_registry_config.get("verify_tls", True),
            proxy=mirror.external_registry_config.get("proxy", {}),
        )

    if not result.success:
        raise RepoMirrorSkopeoException(
            "skopeo inspect failed: %s" % _skopeo_inspect_failure(result),
            result.stdout,
            result.stderr,
        )

    return result.tags


def lookup_manifest_digest(skopeo, mirror, tag_name, verbose_logs=False):
    """ Looks up the digest of the manifest pointed to by the given tag name, via skopeo
        and returns it or raises a RepoMirrorSkopeoException
    """
    username, password = _credentials(mirror)

    with database.CloseForLongOperation(app.config):
        result = skopeo.lookup_manifest_digest(
            "docker://%s:%s" % (mirror.external_reference, tag_name),
            username=username,
            password=password,
            verbose_logs=verbose_logs,
            verify_tls=mirror.external_registry_config.get("verify_tls", True),
            proxy=mirror.external_registry_config.get("proxy", {}),
        )

    if not result.success:
        raise RepoMirrorSkopeoException(
            "skopeo inspect failed: %s" % _skopeo_inspect_failure(result),
            result.stdout,
            result.stderr,
        )

    return result.tags[0]


def _credentials(mirror):
    username = (
        mirror.external_registry_username.decrypt() if mirror.external_registry_username else None
    )
    password = (
        mirror.external_registry_password.decrypt() if mirror.external_registry_password else None
    )

    return username, password


def _skopeo_inspect_failure(result):
    """
    Custom processing of skopeo error messages for user friendly description.

    :param result: SkopeoResults object
    :return: Message to display
    """

    lines = result.stderr.split("\n")
    for line in lines:
        if re.match(".*Error reading manifest.*", line):
            return "No matching tags, including 'latest', to inspect for tags list"

    return "(see output)"
